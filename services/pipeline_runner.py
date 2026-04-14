import json
import os
import queue
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
import time

try:
    import psutil
except Exception:
    psutil = None


BACKEND_DIR = Path(__file__).resolve().parent.parent
PIPELINE_DIR = BACKEND_DIR / "pipeline"
_DEFAULT_READONLY = os.getenv("IRKG_READONLY_RESULTS", "1") != "0"
_runtime_readonly = _DEFAULT_READONLY

STAGE_DEFS = [
    {"id": "stage00", "name": "Domain Filter (S_con pre-compute)", "pattern": "[Stage 00]"},
    {"id": "stage01", "name": "Build TF-IDF vectorizers", "pattern": "[Stage 01]"},
    {"id": "stage02", "name": "Generate top-k candidates", "pattern": "[Stage 02]"},
    {"id": "stage03", "name": "Compute graph cohesion (S_gr)", "pattern": "[Stage 03]"},
    {"id": "stage04", "name": "Hybrid scoring + acceptance gate", "pattern": "[Stage 04]"},
    {"id": "stage05", "name": "Evaluation + ablation table", "pattern": "[Stage 05]"},
    {"id": "stage05b", "name": "Coverage by ranah", "pattern": "[Stage 05b]"},
    {"id": "t10", "name": "CRI computation", "pattern": "[t10]"},
    {"id": "stage06", "name": "External consistency validation", "pattern": "[Stage 06]"},
    {"id": "db", "name": "Load outputs to DB", "pattern": "[DB]"},
]

_jobs = {}
_lock = threading.Lock()


def is_readonly_mode() -> bool:
    return _runtime_readonly


def get_runtime_mode() -> dict:
    return {
        "readonly": is_readonly_mode(),
        "mode_name": "research_locked" if is_readonly_mode() else "experimental",
        "default_readonly": _DEFAULT_READONLY,
    }


def set_runtime_mode(readonly: bool) -> dict:
    global _runtime_readonly
    _runtime_readonly = bool(readonly)
    return get_runtime_mode()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _make_job(mode: str):
    job_id = str(uuid.uuid4())
    return {
        "job_id": job_id,
        "mode": mode,
        "status": "queued",
        "created_at": _now(),
        "started_at": None,
        "finished_at": None,
        "current_stage": None,
        "progress": 0.0,
        "last_error": None,
        "logs": [],
        "events": queue.Queue(),
        "stages": [
            {
                "id": s["id"],
                "name": s["name"],
                "status": "pending",
                "started_at": None,
                "finished_at": None,
            }
            for s in STAGE_DEFS
        ],
    }


def _append_event(job, event_type: str, payload: dict):
    event = {"type": event_type, "timestamp": _now(), **payload}
    job["logs"].append(event)
    if len(job["logs"]) > 1500:
        job["logs"] = job["logs"][-1500:]
    job["events"].put(event)


def _set_stage(job, stage_id: str, status: str):
    for i, s in enumerate(job["stages"]):
        if s["id"] == stage_id:
            if status == "running" and s["started_at"] is None:
                s["started_at"] = _now()
            if status in {"completed", "failed"}:
                s["finished_at"] = _now()
            s["status"] = status
            job["current_stage"] = stage_id
            job["progress"] = round(((i + (0.5 if status == "running" else 1)) / len(job["stages"])) * 100, 1)
            _append_event(job, "stage", {"stage_id": stage_id, "stage_status": status})
            break


def _infer_stage(line: str):
    for s in STAGE_DEFS:
        if s["pattern"] in line:
            return s["id"]
    return None


def _run_subprocess(job, cmd, workdir: Path):
    proc = subprocess.Popen(
        cmd,
        cwd=str(workdir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    active_stage = None
    assert proc.stdout is not None
    start_ts = time.time()
    line_count = 0
    last_metric_ts = start_ts
    for raw_line in proc.stdout:
        line = raw_line.rstrip()
        if not line:
            continue
        line_count += 1
        _append_event(job, "log", {"message": line})
        now_ts = time.time()
        if now_ts - last_metric_ts >= 1.0:
            elapsed = max(now_ts - start_ts, 1e-6)
            throughput = round(line_count / elapsed, 2)
            metric = {"throughput_logs_per_sec": throughput}
            if psutil:
                metric.update({
                    "cpu_percent": psutil.cpu_percent(interval=None),
                    "memory_percent": psutil.virtual_memory().percent,
                })
            _append_event(job, "metric", metric)
            last_metric_ts = now_ts
        stage_id = _infer_stage(line)
        if stage_id and stage_id != active_stage:
            if active_stage:
                _set_stage(job, active_stage, "completed")
            active_stage = stage_id
            _set_stage(job, active_stage, "running")
    rc = proc.wait()
    if active_stage:
        _set_stage(job, active_stage, "completed" if rc == 0 else "failed")
    return rc


def _run_job(job):
    try:
        job["status"] = "running"
        job["started_at"] = _now()
        _append_event(job, "status", {"status": "running"})
        mode = job["mode"]

        run_pipeline = mode in {"all", "pipeline_only"} and not is_readonly_mode()
        if run_pipeline:
            pipeline_cmd = ["python", "-u", "main.py", "--all"] if mode == "all" else ["python", "-u", "main.py", "--ablation"]
            rc = _run_subprocess(job, pipeline_cmd, PIPELINE_DIR)
            if rc != 0:
                job["status"] = "failed"
                job["last_error"] = f"Pipeline process gagal (return code {rc})."
                job["finished_at"] = _now()
                _append_event(job, "status", {"status": "failed", "return_code": rc, "error": job["last_error"]})
                _append_event(job, "done", {"status": "failed"})
                return
        else:
            _append_event(
                job,
                "log",
                {"message": "[INFO] Research Locked aktif: skip komputasi pipeline, refresh DB dari output final."},
            )

        db_cmd = ["python", "-u", "-m", "services.db_loader"]
        rc_db = _run_subprocess(job, db_cmd, BACKEND_DIR)
        if rc_db != 0:
            job["status"] = "failed"
            job["last_error"] = f"DB loader gagal (return code {rc_db})."
            job["finished_at"] = _now()
            _append_event(job, "status", {"status": "failed", "return_code": rc_db, "error": job["last_error"]})
            _append_event(job, "done", {"status": "failed"})
            return

        job["status"] = "completed"
        job["finished_at"] = _now()
        job["progress"] = 100.0
        _append_event(job, "status", {"status": "completed"})
        _append_event(job, "done", {"status": "completed"})
    except Exception as exc:
        job["status"] = "failed"
        job["finished_at"] = _now()
        job["last_error"] = str(exc)
        _append_event(job, "status", {"status": "failed", "error": str(exc)})
        _append_event(job, "done", {"status": "failed"})


_last_job_id: str | None = None


def start_pipeline_job(mode: str = "all"):
    global _last_job_id
    job = _make_job(mode=mode)
    with _lock:
        _jobs[job["job_id"]] = job
        _last_job_id = job["job_id"]
    th = threading.Thread(target=_run_job, args=(job,), daemon=True)
    th.start()
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "mode": mode,
        "readonly": is_readonly_mode(),
    }


def get_latest_job_id() -> str | None:
    return _last_job_id


def get_job(job_id: str):
    with _lock:
        return _jobs.get(job_id)


def get_job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        return None
    return {
        "job_id": job["job_id"],
        "mode": job["mode"],
        "status": job["status"],
        "created_at": job["created_at"],
        "started_at": job["started_at"],
        "finished_at": job["finished_at"],
        "current_stage": job["current_stage"],
        "progress": job["progress"],
        "last_error": job.get("last_error"),
        "readonly": is_readonly_mode(),
    }


def get_job_stages(job_id: str):
    job = get_job(job_id)
    if not job:
        return None
    return {"job_id": job_id, "stages": job["stages"], "progress": job["progress"], "status": job["status"]}


def get_stage_output_preview(job_id: str, stage_id: str):
    job = get_job(job_id)
    if not job:
        return None
    stage_logs = [e for e in job["logs"] if e["type"] == "log" and _infer_stage(e["message"]) == stage_id]
    return {
        "job_id": job_id,
        "stage_id": stage_id,
        "line_count": len(stage_logs),
        "log_preview": [x["message"] for x in stage_logs[-30:]],
        "output_hints": _stage_artifact_hints(stage_id),
    }


def _stage_artifact_hints(stage_id: str):
    outputs = BACKEND_DIR / "data" / "outputs"
    hints = {
        "stage01": [outputs / "vectorizer_T1a.pkl", outputs / "vectorizer_T5.pkl"],
        "stage04": [outputs / "accepted_mappings"],
        "stage05": [outputs / "irkg_ablation_final.xlsx"],
        "stage05b": [outputs / "irkg_coverage_by_ranah_summary.csv"],
        "t10": [outputs / "cri_results.xlsx"],
        "stage06": [outputs / "ecv_results.xlsx"],
        "db": [BACKEND_DIR / "data" / "db" / "irkg.db"],
    }
    return [
        {"path": str(p), "exists": p.exists(), "size_bytes": p.stat().st_size if p.exists() else None}
        for p in hints.get(stage_id, [])
    ]


def sse_event_stream(job_id: str):
    job = get_job(job_id)
    if not job:
        yield 'event: error\ndata: {"error":"job not found"}\n\n'
        return

    yield f"event: snapshot\ndata: {json.dumps(get_job_status(job_id))}\n\n"
    while True:
        try:
            evt = job["events"].get(timeout=15)
            yield f"event: {evt['type']}\ndata: {json.dumps(evt)}\n\n"
            if evt["type"] == "done":
                break
        except queue.Empty:
            yield 'event: ping\ndata: {"ok":true}\n\n'
