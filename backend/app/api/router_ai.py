import json
from fastapi import APIRouter, Form, HTTPException
from pathlib import Path
from app.core.config import settings
from app.services.testbench_ai import generate_test_vectors, analyze_hdl_ports

router = APIRouter()

@router.post("/generate-testbench")
async def generate_ai_testbench(
    session_id: str = Form(...),
    top_module: str = Form(...),
    sim_cycles: int = Form(100),
    api_key: str = Form(...)
):
    workspace = settings.WORKSPACES_DIR / session_id
    if not workspace.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    # Find HDL files
    hdl_files = list(workspace.glob("*.v")) + list(workspace.glob("*.sv")) + \
                list(workspace.glob("*.vhd")) + list(workspace.glob("*.vhdl"))
    if not hdl_files:
        raise HTTPException(status_code=400, detail="No HDL files found in session")

    hdl_code = ""
    for f in hdl_files:
        hdl_code += f"// File: {f.name}\n"
        hdl_code += f.read_text(encoding="utf-8", errors="replace")
        hdl_code += "\n\n"

    # Extract ports from the netlist JSON if available
    json_netlist = workspace / "netlist.json"
    ports = []
    if json_netlist.exists():
        try:
            with open(json_netlist) as f:
                netlist = json.load(f)
            mod = netlist.get("modules", {}).get(top_module, {})
            for pname, pinfo in mod.get("ports", {}).items():
                bits = pinfo.get("bits", [])
                width = max(len(bits), 1)
                ports.append({
                    "name": pname,
                    "direction": pinfo.get("direction", "input"),
                    "width": width
                })
        except Exception:
            pass

    if not ports:
        ports = analyze_hdl_ports(hdl_code, top_module)

    try:
        vectors = generate_test_vectors(hdl_code, top_module, ports, sim_cycles, api_key)
    except (ValueError, PermissionError, TimeoutError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Save vectors
    vectors_file = workspace / "test_vectors.json"
    with open(vectors_file, "w") as f:
        json.dump(vectors, f, indent=2)

    return {
        "status": "success",
        "message": f"Generated {len(vectors)} test vectors",
        "vectors_count": len(vectors),
        "port_count": len(ports),
        "ports": ports[:5]
    }

@router.get("/test-vectors/{session_id}")
async def get_test_vectors(session_id: str):
    vectors_file = settings.WORKSPACES_DIR / session_id / "test_vectors.json"
    if not vectors_file.exists():
        raise HTTPException(status_code=404, detail="No AI test vectors found. Generate them first.")

    with open(vectors_file) as f:
        vectors = json.load(f)

    # Show sample
    return {
        "total": len(vectors),
        "sample": vectors[:5] if len(vectors) > 5 else vectors,
        "columns": list(vectors[0].keys()) if vectors else []
    }
