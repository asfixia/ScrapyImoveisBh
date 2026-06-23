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
#os.environ["CRAWL_LABELS"] = "NetImoveis"

# scrapy crawl <label> — value is output JSON suffix (see scrape_output.output_json_path)
SPIDERS: dict[str, str] = {
    #"NetImoveis": "netimoveis",
    #"VivaReal": "vivareal",
    #"QuintoAndar": "quintoandar",
    #"CasaMineira": "casamineira",
}

SPIDER_PYTHON: dict[str, str] = {
    #"ZapImoveis": "ImoveisScrapy/spiders/zapimoveis_scrapy.py",
}

# python <script> — started only after all SPIDERS + SPIDER_PYTHON finish
AFTER_SPIDER: dict[str, str] = {
    #"MergeImoveis": "pipeline/merge.py",
    #"UploadImoveisToDb": "pipeline/upload_to_db.py",
    "UploadImoveisStamped": "pipeline/upload_imoveis_stamped.py",
}

LOG_DIR = PROJECT_ROOT / "logs"
STAGGER_SECONDS = 0.1
POLL_INTERVAL_SECONDS = 0.5
# Comma/semicolon-separated crawl labels (SPIDERS + SPIDER_PYTHON keys). Empty = run all.
CRAWL_LABELS_ENV = "CRAWL_LABELS"

Job = tuple[str, subprocess.Popen[str], threading.Thread, object, Path]


def _all_crawl_labels() -> list[str]:
    return list(SPIDERS) + list(SPIDER_PYTHON)


def _crawl_label_lookup() -> dict[str, str]:
    return {label.casefold(): label for label in _all_crawl_labels()}


def _parse_crawl_labels_env() -> list[str] | None:
    """Return canonical labels from CRAWL_LABELS, or None to run every crawler."""
    raw = os.environ.get(CRAWL_LABELS_ENV, "").strip()
    if not raw:
        return None

    lookup = _crawl_label_lookup()
    selected: list[str] = []
    unknown: list[str] = []

    for part in raw.replace(";", ",").split(","):
        token = part.strip()
        if not token:
            continue
        canonical = lookup.get(token.casefold())
        if token.casefold() == "none":
            return []
        if canonical is None:
            unknown.append(token)
        elif canonical not in selected:
            selected.append(canonical)

    if unknown:
        available = ", ".join(_all_crawl_labels())
        print(
            f"Unknown {CRAWL_LABELS_ENV} label(s): {', '.join(unknown)}. "
            f"Available: {available}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not selected:
        print(f"{CRAWL_LABELS_ENV} is set but no labels were parsed.", file=sys.stderr)
        sys.exit(1)

    return selected


def _selected_crawl_labels() -> list[str]:
    """Labels to run this session (order preserved from SPIDERS then SPIDER_PYTHON)."""
    filter_labels = _parse_crawl_labels_env()
    if filter_labels is None:
        return _all_crawl_labels()
    allowed = set(filter_labels)
    return [label for label in _all_crawl_labels() if label in allowed]


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
        check=True,
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
    """Prefix lines on stdout (Docker); write plain lines to the log file."""

    def __init__(self, label: str, stdout: object, log_file: object) -> None:
        self._prefix = f"[{label}] "
        self._stdout = stdout
        self._log_file = log_file
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
        self._stdout.write(f"{self._prefix}{line}\n")
        stdout_flush = getattr(self._stdout, "flush", None)
        if stdout_flush:
            stdout_flush()
        self._log_file.write(f"{line}\n")
        log_flush = getattr(self._log_file, "flush", None)
        if log_flush:
            log_flush()

    def flush(self) -> None:
        if self._buffer:
            self._write_line(self._buffer)
            self._buffer = ""
        for stream in (self._stdout, self._log_file):
            flush = getattr(stream, "flush", None)
            if flush:
                flush()


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


def _log_path(label: str) -> Path:
    return LOG_DIR / f"{label}.log"


def _read_log_tail(path: Path, lines: int = 25) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"(could not read log: {exc})"
    tail = text.splitlines()[-lines:]
    return "\n".join(tail) if tail else "(log empty)"


def _format_cmd(cmd: list[str]) -> str:
    return " ".join(cmd)


def _start_command(cmd: list[str], label: str) -> Job:
    """Start a subprocess; stream lines to Docker (prefixed) and a log file (plain)."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = _log_path(label)
    log_file = open(log_path, "w", encoding="utf-8", buffering=1)
    tee = _Tee(label, sys.stdout, log_file)

    print(f"[{label}] $ {_format_cmd(cmd)}", flush=True)
    print(f"[{label}] log → {log_path}", flush=True)

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
    return label, proc, reader, log_file, log_path


def start_spider(spider_name: str) -> Job:
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
    return _start_command([sys.executable, "-u", str(path)], job_label)


def _finish_job(
    label: str,
    proc: subprocess.Popen[str],
    reader: threading.Thread,
    log_file: object,
    log_path: Path,
    phase: str,
    started_at: float,
) -> tuple[str, int] | None:
    exit_code = proc.wait()
    reader.join(timeout=60)
    try:
        log_file.close()
    except OSError:
        pass

    elapsed = time.time() - started_at
    if exit_code == 0:
        print(f"[{phase}] {label} finished OK ({elapsed:.0f}s).", flush=True)
        return None

    print(
        f"[{phase}] {label} failed (exit {exit_code}, {elapsed:.0f}s). Log: {log_path}",
        file=sys.stderr,
        flush=True,
    )
    print(_read_log_tail(log_path), file=sys.stderr, flush=True)
    return label, exit_code


def wait_jobs(jobs: list[Job], phase: str) -> list[tuple[str, int]]:
    if not jobs:
        return []

    print(f"Waiting for {len(jobs)} job(s) in phase [{phase}] …", flush=True)
    failed: list[tuple[str, int]] = []
    pending: list[tuple[Job, float]] = [(job, time.time()) for job in jobs]

    while pending:
        still_running: list[tuple[Job, float]] = []
        for job, started_at in pending:
            label, proc, reader, log_file, log_path = job
            if proc.poll() is None:
                still_running.append((job, started_at))
                continue
            result = _finish_job(label, proc, reader, log_file, log_path, phase, started_at)
            if result is not None:
                failed.append(result)
        pending = still_running
        if pending:
            time.sleep(POLL_INTERVAL_SECONDS)

    return failed


def _preflight(spiders_to_run: list[str]) -> None:
    """Fail fast when Scrapy/project layout is broken (common in Docker/Linux)."""
    scrapy_cfg = PROJECT_ROOT / "scrapy.cfg"
    if not scrapy_cfg.is_file():
        print(f"Preflight failed: missing {scrapy_cfg}", file=sys.stderr)
        sys.exit(1)

    scrapy_spiders = [name for name in spiders_to_run if name in SPIDERS]
    if not scrapy_spiders:
        return

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
    missing = [name for name in scrapy_spiders if name not in listed]
    if missing:
        print(
            f"Preflight failed: spider(s) not registered: {', '.join(missing)}",
            file=sys.stderr,
        )
        print("Available:", result.stdout.strip(), file=sys.stderr)
        sys.exit(1)


def main() -> None:
    _configure_stdio()
    crawl_labels = _selected_crawl_labels()
    if os.environ.get(CRAWL_LABELS_ENV, "").strip():
        print(f"Crawl labels ({CRAWL_LABELS_ENV}): {', '.join(crawl_labels)}", flush=True)
    _preflight(crawl_labels)
    crawl_jobs: list[Job] = []

    for label in crawl_labels:
        if label in SPIDERS:
            if spider_is_running(label):
                print(f"{label} already running — skipped.", flush=True)
            else:
                crawl_jobs.append(start_spider(label))
                time.sleep(STAGGER_SECONDS)
        elif label in SPIDER_PYTHON:
            script = SPIDER_PYTHON[label]
            if python_script_is_running(script):
                print(f"{label} ({script}) already running — skipped.", flush=True)
            else:
                crawl_jobs.append(start_python_script(script, label=label))
                time.sleep(STAGGER_SECONDS)

    failed: list[tuple[str, int]] = []
    if crawl_jobs:
        failed.extend(wait_jobs(crawl_jobs, "crawl"))
    else:
        print("No crawl jobs started (SPIDERS + SPIDER_PYTHON).", flush=True)

    after_jobs: list[Job] = []
    for label, script in AFTER_SPIDER.items():
        path = _resolve_script(script)
        if python_script_is_running(path):
            print(f"{label} ({path.name}) already running — skipped.", flush=True)
        else:
            after_jobs.append(start_python_script(path, label=label))
            time.sleep(STAGGER_SECONDS)

    if after_jobs:
        failed.extend(wait_jobs(after_jobs, "after"))
    elif AFTER_SPIDER:
        print("No after jobs started (AFTER_SPIDER).", flush=True)

    if failed:
        names = ", ".join(f"{label}({code})" for label, code in failed)
        print(f"Finished with errors: {names}", file=sys.stderr, flush=True)
        sys.exit(1)

    print("All jobs finished successfully.", flush=True)


if __name__ == "__main__":
    main()
