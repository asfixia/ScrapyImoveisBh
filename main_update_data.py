"""Start crawlers/scripts, wait for each phase, then run AFTER_SPIDER jobs."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

# scrapy crawl <name>
SPIDERS = [
    "NetImoveis",
    "VivaReal",
    "QuintoAndar",
    "CasaMineira",
]

SPIDER_PYTHON: dict[str, str] = {
    "ZapImoveis": "ImoveisScrapy/spiders/zapimoveis_scrapy.py",
}

# python <script> — started only after all SPIDERS + SPIDER_PYTHON finish
AFTER_SPIDER: dict[str, str] = {
    "MergeImoveis": "pipeline/merge.py",
    #"UploadImoveisToDb": "pipeline/upload_to_db.py",
}

LOG_DIR = PROJECT_ROOT / "logs"
STAGGER_SECONDS = 0.1

Job = tuple[str, subprocess.Popen[bytes], object]


def spider_is_running(spider_name: str) -> bool:
    if sys.platform == "win32":
        return _spider_is_running_windows(spider_name)
    return _spider_is_running_unix(spider_name)


def _spider_is_running_unix(spider_name: str) -> bool:
    result = subprocess.run(
        ["pgrep", "-af", f"scrapy crawl {spider_name}"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _run_powershell(script: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        capture_output=True,
        text=True,
        env=env,
        creationflags=flags,
    )


def _count_scrapy_spider_processes_ps(script_body: str, spider_name: str) -> int | None:
    env = os.environ.copy()
    env["SPIDER_TO_CHECK"] = spider_name
    result = _run_powershell(script_body, env=env)
    if result.returncode != 0:
        return None
    out = (result.stdout or "").strip()
    if not out:
        return 0
    try:
        return int(out.splitlines()[-1].strip())
    except ValueError:
        return None


def _spider_is_running_windows(spider_name: str) -> bool:
    _PS_CIM_COUNT = """
    $procs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.CommandLine -and
            ($_.CommandLine -like '*scrapy*') -and
            ($_.CommandLine -like '*crawl*') -and
            ($_.CommandLine -like ('*' + $env:SPIDER_TO_CHECK + '*'))
        }
    ($procs | Measure-Object).Count
    """
    _PS_WMI_COUNT = """
    $procs = Get-WmiObject Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.CommandLine -and
            ($_.CommandLine -like '*scrapy*') -and
            ($_.CommandLine -like '*crawl*') -and
            ($_.CommandLine -like ('*' + $env:SPIDER_TO_CHECK + '*'))
        }
    ($procs | Measure-Object).Count
    """
    count = _count_scrapy_spider_processes_ps(_PS_CIM_COUNT, spider_name)
    if count is None:
        count = _count_scrapy_spider_processes_ps(_PS_WMI_COUNT, spider_name)
    if count is None:
        print(
            f"Warning: could not detect running processes for {spider_name} "
            "(PowerShell/WMI). Assuming not running.",
            file=sys.stderr,
        )
        return False
    return count > 0


def _resolve_script(script: str) -> Path:
    path = Path(script)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def python_script_is_running(script: str | Path) -> bool:
    """True if another process is already running this script path."""
    path = _resolve_script(script)
    needle = path.name
    if sys.platform == "win32":
        env = os.environ.copy()
        env["SCRIPT_TO_CHECK"] = needle
        ps = """
        $n = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object {
                $_.CommandLine -and ($_.CommandLine -like ('*' + $env:SCRIPT_TO_CHECK + '*'))
            }).Count
        Write-Output $n
        """
        result = _run_powershell(ps, env=env)
        if result.returncode != 0:
            return False
        try:
            return int((result.stdout or "0").strip().splitlines()[-1]) > 0
        except ValueError:
            return False
    result = subprocess.run(
        ["pgrep", "-af", needle],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _open_log(label: str) -> object:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return open(LOG_DIR / f"{label}.log", "w", encoding="utf-8")


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    pythonpath = str(PROJECT_ROOT)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{pythonpath}{os.pathsep}{existing}" if existing else pythonpath
    return env


def start_spider(spider_name: str) -> Job:
    print(f"Starting spider: {spider_name}")
    log_file = _open_log(spider_name)
    proc = subprocess.Popen(
        [sys.executable, "-m", "scrapy", "crawl", spider_name],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        cwd=PROJECT_ROOT,
        env=_subprocess_env(),
    )
    return spider_name, proc, log_file


def start_python_script(script: str | Path, label: str | None = None) -> Job:
    path = _resolve_script(script)
    if not path.is_file():
        raise FileNotFoundError(f"Script not found: {path}")
    job_label = label or path.stem
    print(f"Starting {job_label}: {path.name}")
    log_file = _open_log(job_label)
    proc = subprocess.Popen(
        [sys.executable, str(path)],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        cwd=PROJECT_ROOT,
        env=_subprocess_env(),
    )
    return job_label, proc, log_file


def wait_jobs(jobs: list[Job], phase: str) -> list[tuple[str, int]]:
    if not jobs:
        return []

    print(f"Waiting for {len(jobs)} job(s) in phase [{phase}] …")
    failed: list[tuple[str, int]] = []

    for label, proc, log_file in jobs:
        exit_code = proc.wait()
        try:
            log_file.close()
        except OSError:
            pass
        if exit_code == 0:
            print(f"[{phase}] {label} finished OK.")
        else:
            print(f"[{phase}] {label} finished with exit code {exit_code}.", file=sys.stderr)
            failed.append((label, exit_code))

    return failed


def main() -> None:
    crawl_jobs: list[Job] = []

    for spider in dict.fromkeys(SPIDERS):
        if spider_is_running(spider):
            print(f"{spider} already running — skipped.")
        else:
            crawl_jobs.append(start_spider(spider))
            time.sleep(STAGGER_SECONDS)

    for crawler_name, script in SPIDER_PYTHON.items():
        if python_script_is_running(script):
            print(f"{crawler_name} ({script}) already running — skipped.")
        else:
            crawl_jobs.append(start_python_script(script, label=crawler_name))
            time.sleep(STAGGER_SECONDS)

    failed: list[tuple[str, int]] = []
    if crawl_jobs:
        failed.extend(wait_jobs(crawl_jobs, "crawl"))
    else:
        print("No crawl jobs started (SPIDERS + SPIDER_PYTHON).")

    after_jobs: list[Job] = []
    for label, script in AFTER_SPIDER.items():
        path = _resolve_script(script)
        if python_script_is_running(path):
            print(f"{label} ({path.name}) already running — skipped.")
        else:
            after_jobs.append(start_python_script(path, label=label))
            time.sleep(STAGGER_SECONDS)

    if after_jobs:
        failed.extend(wait_jobs(after_jobs, "after"))
    elif AFTER_SPIDER:
        print("No after jobs started (AFTER_SPIDER).")

    if failed:
        names = ", ".join(f"{label}({code})" for label, code in failed)
        print(f"Finished with errors: {names}", file=sys.stderr)
        sys.exit(1)

    print("All jobs finished successfully.")


if __name__ == "__main__":
    main()
