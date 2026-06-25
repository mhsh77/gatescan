"""Mark 2 — API Router for multi-agent cognitive testbench pipeline."""

import json
import threading
import os
import time
from fastapi import APIRouter, Form, HTTPException
from pathlib import Path
from app.core.config import settings
from app.core.progress import progress
from app.services.mark2_orchestrator import run_pipeline

router = APIRouter()

def _run_mark2_task(task_id: str, session_id: str, hdl_code: str, api_key: str):
    workspace = settings.WORKSPACES_DIR / session_id
    progress.create(task_id)
    progress.set_status(task_id, "processing")
    progress.set_progress(task_id, 0, "Starting Mark 2 pipeline...")

    try:
        netlist_json = None
        json_path = workspace / "netlist.json"
        if json_path.exists():
            with open(json_path) as f:
                netlist_json = json.load(f)

        def cb(pct, detail):
            progress.set_progress(task_id, pct, detail)

        result = run_pipeline(
            hdl_code=hdl_code,
            session_id=session_id,
            workspace=workspace,
            api_key=api_key,
            netlist_json=netlist_json,
            progress_cb=cb
        )

        progress.set_status(task_id, "completed", result=result)

    except Exception as e:
        progress.set_status(task_id, "failed", error=str(e))


@router.post("/run")
async def run_mark2(
    session_id: str = Form(...),
    top_module: str = Form(...),
    api_key: str = Form(...)
):
    workspace = settings.WORKSPACES_DIR / session_id
    if not workspace.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    hdl_files = list(workspace.glob("*.v")) + list(workspace.glob("*.sv")) + \
                list(workspace.glob("*.vhd")) + list(workspace.glob("*.vhdl"))
    if not hdl_files:
        raise HTTPException(status_code=400, detail="No HDL files in session")

    hdl_code = ""
    for f in hdl_files:
        hdl_code += f"// File: {f.name}\n{f.read_text(encoding='utf-8', errors='replace')}\n\n"

    task_id = f"mark2_{session_id}"
    thread = threading.Thread(
        target=_run_mark2_task,
        args=(task_id, session_id, hdl_code, api_key),
        daemon=True
    )
    thread.start()

    return {"task_id": task_id, "status": "processing"}


@router.post("/quick-run")
async def quick_mark2_run(
    session_id: str = Form(...),
    top_module: str = Form(...),
    api_key: str = Form(...)
):
    """Run the full pipeline and return the generated testbench + review inline (no polling)."""
    workspace = settings.WORKSPACES_DIR / session_id
    if not workspace.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    hdl_files = list(workspace.glob("*.v")) + list(workspace.glob("*.sv")) + \
                list(workspace.glob("*.vhd")) + list(workspace.glob("*.vhdl"))
    if not hdl_files:
        raise HTTPException(status_code=400, detail="No HDL files in session")

    hdl_code = ""
    for f in hdl_files:
        hdl_code += f"// File: {f.name}\n{f.read_text(encoding='utf-8', errors='replace')}\n\n"

    netlist_json = None
    json_path = workspace / "netlist.json"
    if json_path.exists():
        with open(json_path) as f:
            netlist_json = json.load(f)

    try:
        result = run_pipeline(hdl_code, session_id, workspace, api_key, netlist_json)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}")
async def get_status(task_id: str):
    state = progress.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return state


@router.get("/physiology/{session_id}")
async def get_physiology(session_id: str):
    path = settings.WORKSPACES_DIR / session_id / "mark2_physiology.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Run Mark 2 pipeline first")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/testbench/{session_id}")
async def get_testbench(session_id: str):
    path = settings.WORKSPACES_DIR / session_id / "ai_testbench.py"
    if not path.exists():
        raise HTTPException(status_code=404, detail="No AI testbench generated yet")
    return {"code": path.read_text(encoding="utf-8")}


@router.get("/review/{session_id}")
async def get_review(session_id: str):
    for f in sorted(Path(settings.WORKSPACES_DIR / session_id).glob("mark2_review_*.json"), reverse=True):
        return json.loads(f.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404, detail="No review found")
