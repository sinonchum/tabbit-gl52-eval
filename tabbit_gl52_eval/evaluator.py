
"""
Feiyue Capability Classification Engine

Implements the Feiyue rules.py evaluation logic for classifying an LLM's
programming capability as weak, mid, or strong based on benchmark results.

Rules (from feiyue_core/capability/rules.py):
  - PROMOTE to strong: ≥3 independent successes AND teacher_call_rate ≤ 0
  - DEMOTE to weak: same repeated_mistake_category ≥ 2 times
  - KEEP at mid: all other cases
  - ESCALATE_TO_TEACHER: if any unsafe records exist

This module is provider-free — it only consumes WorkerPerformanceRecord-like
data and produces CapabilityRecommendation outputs.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class WorkerTaskResult(str, Enum):
    """Outcome of a single benchmark task attempt."""
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    UNSAFE = "unsafe"


class RecommendationAction(str, Enum):
    """Routing recommendation for a capability level."""
    PROMOTE = "promote"          # → strong
    KEEP = "keep"                # → mid
    DEMOTE = "demote"            # → weak
    ESCALATE_TO_TEACHER = "escalate_to_teacher"


@dataclass
class CapabilityRecord:
    """A single benchmark task result (analogous to WorkerPerformanceRecord)."""
    record_id: str
    model_id: str
    task_id: str
    capability_level: str
    result: WorkerTaskResult
    category: str
    repeated_mistake_category: str | None = None
    teacher_call_count: int = 0
    verifier_result: str = ""
    pytest_passed: int = 0
    pytest_failed: int = 0


@dataclass
class CapabilityThresholds:
    """Tunable thresholds for promotion/demotion decisions."""
    min_promotion_successes: int = 3
    max_teacher_call_rate: float = 0.0
    max_repeated_mistakes_before_demotion: int = 2


@dataclass
class CapabilityRecommendation:
    """Output of the classification engine."""
    model_id: str
    capability_level: str  # abstract level being evaluated (e.g., "coding")
    action: RecommendationAction
    rationale: str
    passed_count: int = 0
    failed_count: int = 0
    blocked_count: int = 0
    mistake_counts: dict[str, int] = field(default_factory=dict)
    teacher_call_rate: float = 0.0

    @property
    def is_strong(self) -> bool:
        return self.action == RecommendationAction.PROMOTE

    @property
    def is_weak(self) -> bool:
        return self.action == RecommendationAction.DEMOTE

    @property
    def is_mid(self) -> bool:
        return self.action == RecommendationAction.KEEP

    def render_markdown(self) -> str:
        """Render a human-readable classification report."""
        lines = [
            f"# Capability Classification: {self.model_id}",
            "",
            f"**Level:** {self.capability_level}",
            f"**Action:** {self.action.value.upper()}",
            "",
            "## Results",
            f"- Passed: {self.passed_count}",
            f"- Failed: {self.failed_count}",
            f"- Blocked: {self.blocked_count}",
            f"- Teacher call rate: {self.teacher_call_rate:.2f}",
            "",
            "## Mistake Categories",
        ]
        if self.mistake_counts:
            for cat, count in sorted(self.mistake_counts.items()):
                lines.append(f"- {cat}: {count}")
        else:
            lines.append("- None")

        lines.extend([
            "",
            "## Rationale",
            self.rationale,
        ])
        return "\n".join(lines)


def classify(
    model_id: str,
    records: Iterable[CapabilityRecord],
    capability_level: str = "coding",
    thresholds: CapabilityThresholds | None = None,
) -> CapabilityRecommendation:
    """Classify a model as weak/mid/strong based on benchmark records.

    Implements the Feiyue capability evaluation logic.

    Args:
        model_id: The model identifier (e.g., "GLM-5.2").
        records: Benchmark task results for this model.
        capability_level: Label for the evaluated capability dimension.
        thresholds: Overridable decision thresholds.

    Returns:
        CapabilityRecommendation with the classification verdict.
    """
    if thresholds is None:
        thresholds = CapabilityThresholds()

    records_list = list(records)

    # ── Count unsafe records (requires teacher escalation) ──────────
    unsafe = [r for r in records_list if r.result == WorkerTaskResult.UNSAFE]
    if unsafe:
        return CapabilityRecommendation(
            model_id=model_id,
            capability_level=capability_level,
            action=RecommendationAction.ESCALATE_TO_TEACHER,
            rationale=(
                f"{len(unsafe)} unsafe record(s) require teacher escalation "
                f"before routing changes."
            ),
            passed_count=0,
            failed_count=0,
            blocked_count=len(unsafe),
        )

    # ── Tally results ───────────────────────────────────────────────
    passed = [r for r in records_list if r.result == WorkerTaskResult.PASSED]
    failed = [r for r in records_list if r.result == WorkerTaskResult.FAILED]
    blocked = [r for r in records_list if r.result == WorkerTaskResult.BLOCKED]

    # ── Count repeated mistakes ─────────────────────────────────────
    mistake_categories = [
        r.repeated_mistake_category
        for r in failed
        if r.repeated_mistake_category is not None
    ]
    mistake_counts = Counter(mistake_categories)

    # ── Compute teacher call rate ───────────────────────────────────
    total_with_teacher = sum(
        1 for r in records_list if r.teacher_call_count > 0
    )
    teacher_call_rate = (
        total_with_teacher / len(records_list) if records_list else 0.0
    )

    # ── Decision logic ──────────────────────────────────────────────
    passed_count = len(passed)

    # Demotion: same mistake repeated ≥ threshold
    if mistake_counts and max(mistake_counts.values()) >= thresholds.max_repeated_mistakes_before_demotion:
        worst_category: str = max(mistake_counts, key=lambda k: mistake_counts[k])
        return CapabilityRecommendation(
            model_id=model_id,
            capability_level=capability_level,
            action=RecommendationAction.DEMOTE,
            rationale=(
                f"'{worst_category}' repeated {mistake_counts[worst_category]} "
                f"time(s), meeting demotion threshold "
                f"{thresholds.max_repeated_mistakes_before_demotion}."
            ),
            passed_count=passed_count,
            failed_count=len(failed),
            blocked_count=len(blocked),
            mistake_counts=dict(mistake_counts),
            teacher_call_rate=teacher_call_rate,
        )

    # Promotion: enough successes, no teacher reliance
    if (
        passed_count >= thresholds.min_promotion_successes
        and teacher_call_rate <= thresholds.max_teacher_call_rate
    ):
        return CapabilityRecommendation(
            model_id=model_id,
            capability_level=capability_level,
            action=RecommendationAction.PROMOTE,
            rationale=(
                f"{passed_count} independent successes "
                f"(threshold: {thresholds.min_promotion_successes}), "
                f"teacher call rate {teacher_call_rate:.2f} "
                f"(threshold: ≤{thresholds.max_teacher_call_rate})."
            ),
            passed_count=passed_count,
            failed_count=len(failed),
            blocked_count=len(blocked),
            mistake_counts=dict(mistake_counts),
            teacher_call_rate=teacher_call_rate,
        )

    # Otherwise: keep at current level
    return CapabilityRecommendation(
        model_id=model_id,
        capability_level=capability_level,
        action=RecommendationAction.KEEP,
        rationale=(
            f"{passed_count} successes, "
            f"teacher call rate {teacher_call_rate:.2f}, "
            f"no repeated mistake category reached "
            f"{thresholds.max_repeated_mistakes_before_demotion}."
        ),
        passed_count=passed_count,
        failed_count=len(failed),
        blocked_count=len(blocked),
        mistake_counts=dict(mistake_counts),
        teacher_call_rate=teacher_call_rate,
    )


# ── Convenience aliases ─────────────────────────────────────────────────

def is_strong(model_id: str, records: Iterable[CapabilityRecord]) -> bool:
    """Return True if the model qualifies as strong."""
    return classify(model_id, records).is_strong


def is_weak(model_id: str, records: Iterable[CapabilityRecord]) -> bool:
    """Return True if the model qualifies as weak."""
    return classify(model_id, records).is_weak
