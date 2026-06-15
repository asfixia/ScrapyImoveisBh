"""Start crawlers/scripts, wait for each phase, then run AFTER_SPIDER jobs."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
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
MIN_CRAWL_SECONDS = float(os.environ.get("MIN_CRAWL_SECONDS", "30"))
MIN_LOG_BYTES = 500
MIN_LOG_LINES = 15
MIN_OUTPUT_BYTES = 200
MIN_LISTINGS = int(os.environ.get("MIN_CRAWL_LISTINGS", "1"))
POLL_INTERVAL_SECONDS = 0.5
HEARTBEAT_SECONDS = 30.0

WROTE_LISTINGS_RE = re.compile(
    r"wrote\s+(\d+)\s+(?:unique\s+)?listing",
    re.IGNORECASE,
)

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

Job = tuple[str, subprocess.Popen[str], threading.Thread, object, float, Path, "_StreamStats"]


@dataclass
class _StreamStats:
    lines: int = 0
    bytes_written: int = 0


@dataclass
class _JobReport:
    label: str
    elapsed: float
    exit_code: int
    log_path: Path
    log_lines: int
    log_bytes: int
    stream_lines: int
    output_path: Path | None
    output_bytes: int
    listing_count: int | None
    wrote_in_log: int | None

    def format_summary(self) -> str:
        output = "none"
        if self.output_path is not None:
            output = f"{self.output_path.name} ({self.output_bytes} B"
            if self.listing_count is not None:
                output += f", {self.listing_count} listings"
            output += ")"
        return (
            f"log={self.log_lines} lines/{self.log_bytes} B, "
            f"stream={self.stream_lines} lines, "
            f"output={output}, "
            f"exit={self.exit_code}, "
            f"{self.elapsed:.1f}s"
        )


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

    def __init__(self, label: str, stats: _StreamStats, *streams: object) -> None:
        self._prefix = f"[{label}] "
        self._stats = stats
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
        self._stats.lines += 1
        self._stats.bytes_written += len(text.encode("utf-8"))
        for stream in self._streams:
            stream.write(text)
            flush = getattr(stream, "flush", None)
            if flush:
                flush()

    def flush(self) -> None:
        if self._buffer:
            self._write_line(self._buffer)
            self._buffer = ""
        for stream in self._streams:
            stream.flush()


def _configure_stdio() -> None:
    """Line-buffer stdout/stderr so Docker captures job logs as they arrive."""
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name)
        try:
            stream.reconfigure(line_buffering=True, write_through=True)
        except (AttributeError, OSError, ValueError):
            try:
                stream.reconfigure(line_buffering=True)
            except (AttributeError, OSError, ValueError):
                pass


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


def _log_stats(log_path: Path) -> tuple[int, int]:
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0, 0
    lines = text.splitlines()
    return len(lines), len(text.encode("utf-8"))


def _fresh_output_file(label: str, started_at: float) -> tuple[Path | None, int, int | None]:
    suffix = _output_suffix(label)
    if not suffix:
        return None, 0, None

    out_dir = _output_dir()
    candidates = [
        path
        for path in out_dir.glob(f"*_{suffix}.json")
        if path.stat().st_mtime >= started_at - 2
    ]
    if not candidates:
        return None, 0, None

    newest = max(candidates, key=lambda path: path.stat().st_mtime)
    raw = newest.read_bytes()
    listing_count: int | None
    try:
        payload = json.loads(raw.decode("utf-8"))
        listing_count = len(payload) if isinstance(payload, dict) else None
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        listing_count = None
    return newest, len(raw), listing_count


def _wrote_listings_in_log(log_text: str) -> int | None:
    counts = [int(match.group(1)) for match in WROTE_LISTINGS_RE.finditer(log_text)]
    return max(counts) if counts else None


def _build_job_report(
    label: str,
    log_path: Path,
    started_at: float,
    exit_code: int,
    stats: _StreamStats,
) -> _JobReport:
    elapsed = time.time() - started_at
    log_lines, log_bytes = _log_stats(log_path)
    output_path, output_bytes, listing_count = _fresh_output_file(label, started_at)
    try:
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        log_text = ""
    return _JobReport(
        label=label,
        elapsed=elapsed,
        exit_code=exit_code,
        log_path=log_path,
        log_lines=log_lines,
        log_bytes=log_bytes,
        stream_lines=stats.lines,
        output_path=output_path,
        output_bytes=output_bytes,
        listing_count=listing_count,
        wrote_in_log=_wrote_listings_in_log(log_text),
    )


def _validate_crawl_job(report: _JobReport) -> str | None:
    """Return an error message when exit_code 0 still looks like a failed crawl."""
    if report.exit_code != 0:
        return None

    if report.stream_lines == 0 and report.log_lines == 0:
        return (
            "no subprocess output captured — logging pipe may be broken or the "
            "child process never started"
        )

    if report.log_bytes < MIN_LOG_BYTES or report.log_lines < MIN_LOG_LINES:
        return (
            f"log too small ({report.log_lines} lines, {report.log_bytes} B, "
            f"{report.elapsed:.1f}s)"
        )

    if not any(marker in report.log_path.read_text(encoding="utf-8", errors="replace") for marker in CRAWL_LOG_MARKERS):
        return "log missing expected crawl markers (Scrapy/spider output)"

    if report.elapsed < MIN_CRAWL_SECONDS:
        return (
            f"finished too fast ({report.elapsed:.1f}s < {MIN_CRAWL_SECONDS:.0f}s) — "
            "real crawls take longer; likely immediate exit or empty run"
        )

    if report.output_path is None:
        suffix = _output_suffix(report.label)
        return f"no fresh output file *_{suffix}.json written during this run"

    if report.output_bytes < MIN_OUTPUT_BYTES:
        return (
            f"output file too small ({report.output_bytes} B): "
            f"{report.output_path.name}"
        )

    listings = report.listing_count
    if listings is not None and listings < MIN_LISTINGS:
        return f"output has {listings} listing(s), need at least {MIN_LISTINGS}"

    wrote = report.wrote_in_log
    if wrote is not None and wrote < MIN_LISTINGS:
        return f"log reports only {wrote} listing(s) written"

    if listings is None and wrote is None and MIN_LISTINGS > 0:
        return "could not confirm listings in output file or log"

    return None


def _start_command(cmd: list[str], label: str) -> Job:
    """Start a subprocess; stream prefixed lines to stdout and a log file."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = _log_path(label)
    log_file = open(log_path, "w", encoding="utf-8", buffering=1)
    stats = _StreamStats()
    tee = _Tee(label, stats, sys.stdout, log_file)
    started_at = time.time()
    print(f"  → log file: {log_path}", flush=True)
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
                tee.flush()
        finally:
            tee.flush()
            proc.stdout.close()

    reader = threading.Thread(target=_reader, name=f"log-{label}", daemon=True)
    reader.start()
    return label, proc, reader, log_file, started_at, log_path, stats


def start_spider(spider_name: str) -> Job:
    print(f"Starting spider: {spider_name}", flush=True)
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
    print(f"Starting {job_label}: {path.name}", flush=True)
    return _start_command([sys.executable, "-u", str(path)], job_label)


def _finish_job(
    label: str,
    proc: subprocess.Popen[str],
    reader: threading.Thread,
    log_file: object,
    started_at: float,
    log_path: Path,
    stats: _StreamStats,
    phase: str,
) -> tuple[str, int] | None:
    exit_code = proc.wait()
    reader.join(timeout=60)
    try:
        log_file.close()
    except OSError:
        pass

    report = _build_job_report(label, log_path, started_at, exit_code, stats)
    print(f"[{phase}] {label} report: {report.format_summary()}", flush=True)

    validation_error = None
    if phase == "crawl":
        validation_error = _validate_crawl_job(report)

    if exit_code != 0:
        print(
            f"[{phase}] {label} FAILED (exit {exit_code}). See {log_path}",
            file=sys.stderr,
            flush=True,
        )
        print(_read_log_tail(log_path), file=sys.stderr, flush=True)
        return label, exit_code if exit_code != 0 else 1

    if validation_error:
        print(
            f"[{phase}] {label} FAILED: {validation_error}. See {log_path}",
            file=sys.stderr,
            flush=True,
        )
        print(_read_log_tail(log_path), file=sys.stderr, flush=True)
        return label, 1

    print(f"[{phase}] {label} OK", flush=True)
    return None


def wait_jobs(jobs: list[Job], phase: str) -> list[tuple[str, int]]:
    if not jobs:
        return []

    print(f"Waiting for {len(jobs)} job(s) in phase [{phase}] …", flush=True)
    failed: list[tuple[str, int]] = []
    pending = list(jobs)
    last_heartbeat = time.time()

    while pending:
        still_running: list[Job] = []
        for job in pending:
            label, proc, reader, log_file, started_at, log_path, stats = job
            if proc.poll() is None:
                still_running.append(job)
                continue
            result = _finish_job(
                label, proc, reader, log_file, started_at, log_path, stats, phase
            )
            if result is not None:
                failed.append(result)
        pending = still_running
        if pending:
            now = time.time()
            if now - last_heartbeat >= HEARTBEAT_SECONDS:
                for job in pending:
                    label, proc, _reader, _log_file, started_at, log_path, stats = job
                    log_lines, log_bytes = _log_stats(log_path)
                    elapsed = now - started_at
                    print(
                        f"[{phase}] {label} still running ({elapsed:.0f}s) — "
                        f"log {log_lines} lines / {log_bytes} B, stream {stats.lines} lines",
                        flush=True,
                    )
                last_heartbeat = now
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
    _configure_stdio()
    print(f"Project root: {PROJECT_ROOT}", flush=True)
    print(f"Log directory: {LOG_DIR}", flush=True)
    print(f"Output directory: {_output_dir()}", flush=True)
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
