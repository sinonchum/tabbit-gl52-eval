
"""
Benchmark Runner

Orchestrates the full evaluation pipeline:
  1. Set up benchmark task directories
  2. Send each prompt to GLM-5.2 via Tabbit CDP
  3. Extract code from model responses
  4. Run pytest verifiers on the extracted code
  5. Classify results using the Feiyue rules engine
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path

from .cdp_client import TabbitCDPClient, TabbitCDPError
from .code_extractor import extract_code_block
from .evaluator import (
    CapabilityRecord,
    CapabilityRecommendation,
    WorkerTaskResult,
    classify,
)
from .benchmarks import BenchmarkTask, DEFAULT_BENCHMARKS

logger = logging.getLogger(__name__)


class RunnerError(Exception):
    """Raised when the benchmark runner encounters a fatal error."""
    pass


async def run_benchmarks(
    tasks: list[BenchmarkTask] | None = None,
    *,
    model_id: str = "GLM-5.2",
    cdp_port: int = 9222,
    output_dir: Path | None = None,
) -> tuple[list[CapabilityRecord], CapabilityRecommendation]:
    """Run the full benchmark suite against GLM-5.2 via Tabbit.

    Args:
        tasks: Benchmark tasks to run (default: DEFAULT_BENCHMARKS).
        model_id: Model identifier for result records.
        cdp_port: Chrome DevTools Protocol port for Tabbit.
        output_dir: Directory for task artifacts (auto-created if None).

    Returns:
        Tuple of (individual records, aggregate classification).

    Raises:
        RunnerError: if CDP connection fails or all tasks are blocked.
    """
    if tasks is None:
        tasks = DEFAULT_BENCHMARKS

    work_dir = output_dir or Path(tempfile.mkdtemp(prefix="tabbit_feiyue_"))
    work_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Running %d benchmark tasks in %s", len(tasks), work_dir)

    records: list[CapabilityRecord] = []

    async with TabbitCDPClient(debug_port=cdp_port) as client:
        for i, task in enumerate(tasks):
            logger.info("[%d/%d] %s", i + 1, len(tasks), task.task_id)

            record = await _run_single_task(client, task, model_id, work_dir)
            records.append(record)

            status_icon = _icon(record.result)
            logger.info(
                "  %s %s (%dP/%dF)",
                status_icon,
                record.result.value,
                record.pytest_passed,
                record.pytest_failed,
            )

    recommendation = classify(model_id, records)

    logger.info(
        "Classification: %s (%s)",
        recommendation.action.value.upper(),
        "✅ STRONG" if recommendation.is_strong
        else "⚠️ WEAK" if recommendation.is_weak
        else "— MID",
    )

    return records, recommendation


async def _run_single_task(
    client: TabbitCDPClient,
    task: BenchmarkTask,
    model_id: str,
    work_dir: Path,
) -> CapabilityRecord:
    """Execute one benchmark task end-to-end."""
    task_dir = work_dir / task.task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    # Write setup files
    for filename, content in task.setup_files.items():
        (task_dir / filename).write_text(content)

    try:
        # Send prompt and get response
        response = await client.send_and_read(task.prompt)

        if not response:
            return CapabilityRecord(
                record_id=f"rec-{task.task_id}",
                model_id=model_id,
                task_id=task.task_id,
                capability_level=task.capability_level,
                result=WorkerTaskResult.BLOCKED,
                category=task.category,
                verifier_result="No response from model",
            )

        # Extract and save code
        code = extract_code_block(response)
        if not code:
            return CapabilityRecord(
                record_id=f"rec-{task.task_id}",
                model_id=model_id,
                task_id=task.task_id,
                capability_level=task.capability_level,
                result=WorkerTaskResult.BLOCKED,
                category=task.category,
                repeated_mistake_category=task.category,
                verifier_result="No code block found in response",
            )

        (task_dir / task.target_file).write_text(code)

        # Syntax check
        try:
            compile(code, task.target_file, "exec")
        except SyntaxError as se:
            return CapabilityRecord(
                record_id=f"rec-{task.task_id}",
                model_id=model_id,
                task_id=task.task_id,
                capability_level=task.capability_level,
                result=WorkerTaskResult.FAILED,
                category=task.category,
                repeated_mistake_category=task.category,
                verifier_result=f"Syntax error: {se}",
            )

        # Run pytest
        result = subprocess.run(
            task.verifier_command,
            cwd=task_dir,
            capture_output=True,
            text=True,
            timeout=task.timeout_seconds,
        )

        output = result.stdout + "\n" + result.stderr
        passed = output.count("PASSED")
        failed = output.count("FAILED")

        passed_all = result.returncode == 0

        return CapabilityRecord(
            record_id=f"rec-{task.task_id}",
            model_id=model_id,
            task_id=task.task_id,
            capability_level=task.capability_level,
            result=WorkerTaskResult.PASSED if passed_all else WorkerTaskResult.FAILED,
            category=task.category,
            repeated_mistake_category=task.category if not passed_all else None,
            verifier_result=output[-500:],
            pytest_passed=passed,
            pytest_failed=failed,
        )

    except TabbitCDPError as e:
        logger.error("CDP error on %s: %s", task.task_id, e)
        return CapabilityRecord(
            record_id=f"rec-{task.task_id}",
            model_id=model_id,
            task_id=task.task_id,
            capability_level=task.capability_level,
            result=WorkerTaskResult.BLOCKED,
            category=task.category,
            verifier_result=str(e),
        )
    except subprocess.TimeoutExpired:
        return CapabilityRecord(
            record_id=f"rec-{task.task_id}",
            model_id=model_id,
            task_id=task.task_id,
            capability_level=task.capability_level,
            result=WorkerTaskResult.FAILED,
            category=task.category,
            repeated_mistake_category=task.category,
            verifier_result="Verifier timed out",
        )


def _icon(result: WorkerTaskResult) -> str:
    """Return a status icon for a task result."""
    return {
        WorkerTaskResult.PASSED: "✅",
        WorkerTaskResult.FAILED: "❌",
        WorkerTaskResult.BLOCKED: "⚠️",
        WorkerTaskResult.UNSAFE: "🚫",
    }.get(result, "?")
