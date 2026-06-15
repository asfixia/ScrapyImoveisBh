"""Start crawlers/scripts, wait for each phase, then run AFTER_SPIDER jobs."""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent

# scrapy crawl <label> — value is output JSON suffix (see scrape_output.output_json_path)
SPIDERS: dict[str, str] = {
    "NetImoveis": "netimoveis",
    "VivaReal": "vivareal",
    "QuintoAndar": "quintoandar",
    "CasaMineira": "casamineira",
}

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
MIN_CRAWL_SECONDS = 8.0
MIN_LOG_BYTES = 120
POLL_INTERVAL_SECONDS = 0.5

CRAWL_LOG_MARKERS = (
    "Scrapy",
    "scrapy",
    "Spider",
    "Crawler",
    "INFO",
    "ERROR",
    "wrote",
    "[ZAP]",
    "[QuintoAndar]",
    "[VivaReal]",
    "CasaMineira",
    "NetImoveis",
)

Job = tuple[str, subprocess.Popen[str], threading.Thread, object, float, Path]


def spider_is_running(spider_name: str) -> bool:
    if sys.platform == "win32":
        return _spider_is_running_windows(spider_name)
    return _spider_is_running_unix(spider_name)


def _pgrep_pattern(needle: str) -> str:
    """Pattern that matches needle but not the pgrep process itself."""
    if len(needle) >= 2:
        return f"[{needle[0]}]{needle[1:]}"
    return needle


def _spider_is_running_unix(spider_name: str) -> bool:
    pattern = _pgrep_pattern(f"scrapy crawl {spider_name}")
    result = subprocess.run(
        ["pgrep", "-f", pattern],
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

def hibernate():
    subprocess.run(
        ["shutdown", "/h"],
        check=True
    )

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
    pattern = _pgrep_pattern(needle)
    result = subprocess.run(
        ["pgrep", "-f", pattern],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


class _Tee:
    """Forward writes to streams, prefixing each line with [label]."""

    def __init__(self, label: str, *streams: object) -> None:
        self._prefix = f"[{label}] "
        self._streams = streams
        self._buffer = ""

    def write(self, data: str) -> int:
        if not data:
            return 0
        self._buffer += data
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._write_line(line)
        return len(data)

    def _write_line(self, line: str) -> None:
        text = f"{self._prefix}{line}\n"
        for stream in self._streams:
            stream.write(text)

    def flush(self) -> None:
        if self._buffer:
            self._write_line(self._buffer)
            self._buffer = ""
        for stream in self._streams:
            stream.flush()


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    pythonpath = str(PROJECT_ROOT)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{pythonpath}{os.pathsep}{existing}" if existing else pythonpath
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONUNBUFFERED", "1")
    return env


def _output_dir() -> Path:
    raw = os.environ.get("SCRAPE_OUTPUT_DIR", "").strip()
    if raw:
        return Path(raw)
    return PROJECT_ROOT / "output"


def _log_path(label: str) -> Path:
    return LOG_DIR / f"{label}.log"


def _output_suffix(label: str) -> str | None:
    """Output JSON suffix for a crawl job label."""
    if label in SPIDERS:
        return SPIDERS[label]
    if label in SPIDER_PYTHON:
        return label.lower()
    return None


def _read_log_tail(path: Path, lines: int = 25) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"(could not read log: {exc})"
    tail = text.splitlines()[-lines:]
    return "\n".join(tail) if tail else "(log empty)"


def _validate_crawl_job(label: str, log_path: Path, started_at: float, exit_code: int) -> str | None:
    """Return an error message when exit_code 0 still looks like a no-op run."""
    if exit_code != 0:
        return None

    elapsed = time.time() - started_at
    try:
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"log unreadable ({exc})"

    if len(log_text.strip()) < MIN_LOG_BYTES:
        return (
            f"log too short ({len(log_text.strip())} chars, {elapsed:.1f}s) — "
            "subprocess likely exited before Scrapy/script logging started"
        )

    if not any(marker in log_text for marker in CRAWL_LOG_MARKERS):
        return "log missing expected crawl markers (Scrapy/spider output)"

    if elapsed < MIN_CRAWL_SECONDS and label in SPIDERS:
        startup_markers = ("Spider opened", "Started crawler", "CrawlerProcess", "scrapy.extensions")
        if not any(marker in log_text for marker in startup_markers):
            return (
                f"finished in {elapsed:.1f}s without Scrapy startup markers — "
                "likely immediate exit on Linux/Docker"
            )

    suffix = _output_suffix(label)
    if suffix:
        out_dir = _output_dir()
        recent = sorted(
            out_dir.glob(f"*_{suffix}.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not recent:
            return f"no output file matching *_{suffix}.json in {out_dir}"
        newest = recent[0]
        if newest.stat().st_mtime < started_at - 2:
            return f"no fresh output file for {label} (latest: {newest.name})"

    return None


def _start_command(cmd: list[str], label: str) -> Job:
    """Start a subprocess; stream prefixed lines to stdout and a log file."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = _log_path(label)
    log_file = open(log_path, "w", encoding="utf-8")
    tee = _Tee(label, sys.stdout, log_file)
    started_at = time.time()
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=PROJECT_ROOT,
        env=_subprocess_env(),
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    def _reader() -> None:
        if proc.stdout is None:
            return
        try:
            for line in proc.stdout:
                tee.write(line)
        finally:
            tee.flush()
            proc.stdout.close()

    reader = threading.Thread(target=_reader, name=f"log-{label}", daemon=True)
    reader.start()
    return label, proc, reader, log_file, started_at, log_path


def start_spider(spider_name: str) -> Job:
    print(f"Starting spider: {spider_name}")
    cmd = [
        sys.executable,
        "-u",
        "-m",
        "scrapy",
        "crawl",
        spider_name,
        "--loglevel=INFO",
    ]
    return _start_command(cmd, spider_name)


def start_python_script(script: str | Path, label: str | None = None) -> Job:
    path = _resolve_script(script)
    if not path.is_file():
        raise FileNotFoundError(f"Script not found: {path}")
    job_label = label or path.stem
    print(f"Starting {job_label}: {path.name}")
    return _start_command([sys.executable, "-u", str(path)], job_label)


def _finish_job(
    label: str,
    proc: subprocess.Popen[str],
    reader: threading.Thread,
    log_file: object,
    started_at: float,
    log_path: Path,
    phase: str,
) -> tuple[str, int] | None:
    exit_code = proc.wait()
    reader.join(timeout=60)
    try:
        log_file.close()
    except OSError:
        pass

    elapsed = time.time() - started_at
    validation_error = None
    if phase == "crawl":
        validation_error = _validate_crawl_job(label, log_path, started_at, exit_code)

    if exit_code != 0:
        print(
            f"[{phase}] {label} failed with exit code {exit_code} ({elapsed:.0f}s). "
            f"Log: {log_path}",
            file=sys.stderr,
        )
        print(_read_log_tail(log_path), file=sys.stderr)
        return label, exit_code if exit_code != 0 else 1

    if validation_error:
        print(
            f"[{phase}] {label} exited 0 but looks invalid ({validation_error}, {elapsed:.1f}s). "
            f"Log: {log_path}",
            file=sys.stderr,
        )
        print(_read_log_tail(log_path), file=sys.stderr)
        return label, 1

    print(f"[{phase}] {label} finished OK ({elapsed:.0f}s). Log: {log_path}")
    return None


def wait_jobs(jobs: list[Job], phase: str) -> list[tuple[str, int]]:
    if not jobs:
        return []

    print(f"Waiting for {len(jobs)} job(s) in phase [{phase}] …")
    failed: list[tuple[str, int]] = []
    pending = list(jobs)

    while pending:
        still_running: list[Job] = []
        for job in pending:
            label, proc, reader, log_file, started_at, log_path = job
            if proc.poll() is None:
                still_running.append(job)
                continue
            result = _finish_job(label, proc, reader, log_file, started_at, log_path, phase)
            if result is not None:
                failed.append(result)
        pending = still_running
        if pending:
            time.sleep(POLL_INTERVAL_SECONDS)

    return failed


def _preflight() -> None:
    """Fail fast when Scrapy/project layout is broken (common in Docker/Linux)."""
    scrapy_cfg = PROJECT_ROOT / "scrapy.cfg"
    if not scrapy_cfg.is_file():
        print(f"Preflight failed: missing {scrapy_cfg}", file=sys.stderr)
        sys.exit(1)

    result = subprocess.run(
        [sys.executable, "-u", "-m", "scrapy", "list"],
        cwd=PROJECT_ROOT,
        env=_subprocess_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        print("Preflight failed: `python -m scrapy list`", file=sys.stderr)
        print(result.stdout or result.stderr, file=sys.stderr)
        sys.exit(1)

    listed = set((result.stdout or "").split())
    missing = [name for name in SPIDERS if name not in listed]
    if missing:
        print(
            f"Preflight failed: spider(s) not registered: {', '.join(missing)}",
            file=sys.stderr,
        )
        print("Available:", result.stdout.strip(), file=sys.stderr)
        sys.exit(1)


def main() -> None:
    _preflight()
    crawl_jobs: list[Job] = []

    for spider_name in SPIDERS:
        if spider_is_running(spider_name):
            print(f"{spider_name} already running — skipped.")
        else:
            crawl_jobs.append(start_spider(spider_name))
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
