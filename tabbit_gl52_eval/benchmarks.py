
"""
Benchmark Task Definitions

Programming tasks spanning Feiyue capability levels L1-L6.
Each task includes:
  - Source files (code skeleton + test suite)
  - Prompt text sent to GLM-5.2
  - Pytest verification command
  - Expected capability level

Tasks are designed to be self-contained: all dependencies are in the
provided source files. No network access or external packages needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BenchmarkTask:
    """A self-contained coding benchmark task.

    Attributes:
        task_id: Unique identifier (e.g., "L1.slugify").
        capability_level: Feiyue capability level (documentation_boilerplate, etc.).
        category: Task category for mistake tracking.
        setup_files: Dict of {filename: content} for pre-written files.
        prompt: The natural-language prompt sent to GLM-5.2.
        verifier_command: Pytest command to validate the solution.
        target_file: The file the model should modify/create.
        timeout_seconds: Max execution time for the verifier.
    """
    task_id: str
    capability_level: str
    category: str
    setup_files: dict[str, str] = field(default_factory=dict)
    prompt: str = ""
    verifier_command: list[str] = field(default_factory=list)
    target_file: str = ""
    timeout_seconds: int = 30


# ── L1: Documentation / Simple Code ─────────────────────────────────────

_TASK_L1_SLUGIFY = BenchmarkTask(
    task_id="L1.slugify",
    capability_level="documentation_boilerplate",
    category="code",
    setup_files={
        "slugify.py": (
            "def slugify(text: str) -> str:\n"
            "    pass  # TODO: implement\n"
        ),
        "test_slugify.py": (
            "from slugify import slugify\n\n"
            "def test_basic():\n"
            '    assert slugify("Hello World") == "hello-world"\n\n'
            "def test_special():\n"
            '    assert slugify("Hello! @World#") == "hello-world"\n\n'
            "def test_multi():\n"
            '    assert slugify("a   b   c") == "a-b-c"\n\n'
            "def test_empty():\n"
            '    assert slugify("") == ""\n\n'
            "def test_already():\n"
            '    assert slugify("hello-world") == "hello-world"\n'
        ),
    },
    prompt=(
        "Implement the slugify function in slugify.py. "
        "Convert text to lowercase, replace non-alphanumeric characters "
        "with hyphens, collapse multiple hyphens into one, and strip "
        "leading/trailing hyphens. "
        "Output ONLY the completed slugify.py file."
    ),
    verifier_command=["pytest", "test_slugify.py", "-v", "--tb=short"],
    target_file="slugify.py",
)


# ── L2: Single-File Bug Fix ─────────────────────────────────────────────

_TASK_L2_BSEARCH = BenchmarkTask(
    task_id="L2.bsearch",
    capability_level="single_file_change",
    category="code",
    setup_files={
        "bsearch.py": (
            "def binary_search(arr, target):\n"
            "    left, right = 0, len(arr)\n"
            "    while left < right:\n"
            "        mid = (left + right) // 2\n"
            "        if arr[mid] == target:\n"
            "            return mid\n"
            "        elif arr[mid] < target:\n"
            "            left = mid + 1\n"
            "        else:\n"
            "            right = mid - 1\n"
            "    return -1\n"
        ),
        "test_bsearch.py": (
            "from bsearch import binary_search\n\n"
            "def test_found():\n"
            "    assert binary_search([1,2,3,4,5], 3) == 2\n\n"
            "def test_not_found():\n"
            "    assert binary_search([1,2,3,4,5], 6) == -1\n\n"
            "def test_first():\n"
            "    assert binary_search([1,2,3,4,5], 1) == 0\n\n"
            "def test_last():\n"
            "    assert binary_search([1,2,3,4,5], 5) == 4\n\n"
            "def test_single():\n"
            "    assert binary_search([1], 1) == 0\n\n"
            "def test_empty():\n"
            "    assert binary_search([], 1) == -1\n"
        ),
    },
    prompt=(
        "Fix the bug in binary_search() in bsearch.py. "
        "The function sometimes misses the last element. "
        "Output ONLY the corrected bsearch.py file."
    ),
    verifier_command=["pytest", "test_bsearch.py", "-v", "--tb=short"],
    target_file="bsearch.py",
)

_TASK_L2_AVERAGE = BenchmarkTask(
    task_id="L2.average",
    capability_level="single_file_change",
    category="code",
    setup_files={
        "stats.py": (
            "def calculate_average(numbers):\n"
            "    '''Returns average or 0 for empty list.'''\n"
            "    total = 0\n"
            "    for n in numbers:\n"
            "        total += n\n"
            "    return total / len(numbers)\n"
        ),
        "test_stats.py": (
            "from stats import calculate_average\n\n"
            "def test_normal():\n"
            "    assert calculate_average([1,2,3,4,5]) == 3.0\n\n"
            "def test_single():\n"
            "    assert calculate_average([42]) == 42.0\n\n"
            "def test_empty():\n"
            "    assert calculate_average([]) == 0\n\n"
            "def test_negatives():\n"
            "    assert calculate_average([-1, 1]) == 0.0\n"
        ),
    },
    prompt=(
        "Fix the bug in calculate_average() in stats.py. "
        "It crashes on empty lists. "
        "Output ONLY the corrected stats.py file."
    ),
    verifier_command=["pytest", "test_stats.py", "-v", "--tb=short"],
    target_file="stats.py",
)


# ── L3: Multi-File Feature ──────────────────────────────────────────────

# Note: Truly multi-file tasks require CDP orchestration across turns.
# For the initial release, we use L4+ tasks that exercise deeper reasoning.

# ── L4: Bounded Debug ───────────────────────────────────────────────────

_TASK_L4_PALINDROME = BenchmarkTask(
    task_id="L4.palindrome",
    capability_level="bounded_debug",
    category="code",
    setup_files={
        "pal.py": (
            "def is_palindrome(s: str) -> bool:\n"
            "    pass  # TODO: implement\n"
        ),
        "test_pal.py": (
            "from pal import is_palindrome\n\n"
            "def test_simple():\n"
            '    assert is_palindrome("racecar") == True\n\n'
            "def test_not_pal():\n"
            '    assert is_palindrome("hello") == False\n\n'
            "def test_case():\n"
            '    assert is_palindrome("RaceCar") == True\n\n'
            "def test_spaces():\n"
            '    assert is_palindrome("A man a plan a canal Panama") == True\n\n'
            "def test_empty():\n"
            '    assert is_palindrome("") == True\n\n'
            "def test_single():\n"
            '    assert is_palindrome("a") == True\n'
        ),
    },
    prompt=(
        "Implement is_palindrome(s) in pal.py. "
        "Ignore case and non-alphanumeric characters. "
        "Output ONLY the completed pal.py file."
    ),
    verifier_command=["pytest", "test_pal.py", "-v", "--tb=short"],
    target_file="pal.py",
)


# ── L5: Module Feature Slice ────────────────────────────────────────────

_TASK_L5_RATELIMITER = BenchmarkTask(
    task_id="L5.ratelimiter",
    capability_level="module_feature_slice",
    category="code",
    setup_files={
        "ratelimit.py": (
            "# TODO: implement RateLimiter\n"
            "pass\n"
        ),
        "test_ratelimit.py": (
            "import time\n"
            "from ratelimit import RateLimiter\n\n"
            "def test_allow_under_limit():\n"
            "    rl = RateLimiter(max_requests=3, window_seconds=10)\n"
            "    assert rl.allow_request() == True\n"
            "    assert rl.allow_request() == True\n"
            "    assert rl.allow_request() == True\n\n"
            "def test_deny_over_limit():\n"
            "    rl = RateLimiter(max_requests=2, window_seconds=10)\n"
            "    assert rl.allow_request() == True\n"
            "    assert rl.allow_request() == True\n"
            "    assert rl.allow_request() == False\n\n"
            "def test_window_reset():\n"
            "    rl = RateLimiter(max_requests=2, window_seconds=0.1)\n"
            "    assert rl.allow_request() == True\n"
            "    assert rl.allow_request() == True\n"
            "    assert rl.allow_request() == False\n"
            "    time.sleep(0.15)\n"
            "    assert rl.allow_request() == True\n"
        ),
    },
    prompt=(
        "Implement the RateLimiter class in ratelimit.py. "
        "Use threading.Lock for thread safety and time.time() for a "
        "sliding window. Constructor: __init__(max_requests, window_seconds). "
        "Method: allow_request() -> bool. "
        "Output ONLY the completed ratelimit.py file."
    ),
    verifier_command=["pytest", "test_ratelimit.py", "-v", "--tb=short"],
    target_file="ratelimit.py",
)


# ── L6: Complex Refactor ────────────────────────────────────────────────

_TASK_L6_ASYNC = BenchmarkTask(
    task_id="L6.async_fetch",
    capability_level="teacher_assisted_complex_repair",
    category="code",
    setup_files={
        "fetcher.py": (
            "import requests\n\n"
            "def fetch_all(urls):\n"
            "    results = []\n"
            "    for url in urls:\n"
            "        resp = requests.get(url, timeout=10)\n"
            "        results.append(resp.json())\n"
            "    return results\n"
        ),
        "test_fetcher.py": (
            "import ast, inspect\n\n"
            "def test_has_async_def():\n"
            "    import fetcher\n"
            "    s = inspect.getsource(fetcher.fetch_all)\n"
            "    tree = ast.parse(s)\n"
            "    funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef))]\n"
            "    assert any(isinstance(f, ast.AsyncFunctionDef) for f in funcs), 'Must use async def'\n\n"
            "def test_has_await():\n"
            '    assert "await" in open("fetcher.py").read(), "Must use await"\n\n'
            "def test_imports_aiohttp():\n"
            '    assert "aiohttp" in open("fetcher.py").read(), "Must import aiohttp"\n\n'
            "def test_has_gather():\n"
            '    assert "gather" in open("fetcher.py").read(), "Must use asyncio.gather"\n\n'
            "def test_has_session():\n"
            '    code = open("fetcher.py").read()\n'
            '    assert "ClientSession" in code or "async with" in code, "Must use aiohttp ClientSession"\n'
        ),
    },
    prompt=(
        "Convert fetch_all() in fetcher.py to use async/await with aiohttp "
        "and asyncio.gather for concurrent requests. "
        "Include try/except error handling per request. "
        "Output ONLY the completed fetcher.py file."
    ),
    verifier_command=["pytest", "test_fetcher.py", "-v", "--tb=short"],
    target_file="fetcher.py",
)


# ── Default Suite ───────────────────────────────────────────────────────

DEFAULT_BENCHMARKS: list[BenchmarkTask] = [
    _TASK_L1_SLUGIFY,
    _TASK_L2_BSEARCH,
    _TASK_L2_AVERAGE,
    _TASK_L4_PALINDROME,
    _TASK_L5_RATELIMITER,
    _TASK_L6_ASYNC,
]
