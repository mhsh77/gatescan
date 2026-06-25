"""Mark 2 — Orchestrator
Coordinates the three agents (Analyzer → Actor → Critic) with optional auto-retry."""

import os
import json
from pathlib import Path
from typing import Optional

from .mark2_analyzer import analyze_design
from .mark2_actor import generate_testbench
from .mark2_critic import review_testbench
from .testbench_ai import analyze_hdl_ports

MAX_RETRIES = 2

def run_pipeline(
    hdl_code: str,
    session_id: str,
    workspace: Path,
    api_key: str,
    netlist_json: Optional[dict] = None,
    progress_cb=None
) -> dict:
    """Run the full Mark 2 pipeline: Analyze → Generate → Review → Save.
    Optionally retries if Critic score is below threshold."""

    if progress_cb:
        progress_cb(5, "Analyzing design with DeepSeek...")

    # Extract ports from netlist JSON
    ports = []
    if netlist_json:
        for mod_name, mod_data in netlist_json.get("modules", {}).items():
            for pname, pinfo in mod_data.get("ports", {}).items():
                bits = pinfo.get("bits", [])
                ports.append({
                    "name": pname,
                    "direction": pinfo.get("direction", "input"),
                    "width": max(len(bits), 1)
                })
    if not ports:
        ports = analyze_hdl_ports(hdl_code, "")

    # Step 1: Analyze
    if progress_cb:
        progress_cb(10, "Analyzing design semantics...")
    physiology = analyze_design(hdl_code, ports, api_key)

    physiology_path = workspace / "mark2_physiology.json"
    with open(physiology_path, "w") as f:
        json.dump(physiology, f, indent=2)

    if progress_cb:
        progress_cb(30, f"Design identified as: {physiology.get('design_type', 'unknown')}")

    # Step 2: Generate (with optional retry loop)
    best_code = None
    best_review = None

    for attempt in range(MAX_RETRIES):
        if progress_cb:
            progress_cb(30 + attempt * 20, f"Generating testbench (attempt {attempt + 1})...")

        testbench_code = generate_testbench(physiology, hdl_code, api_key)

        tb_path = workspace / "mark2_testbench.py"
        with open(tb_path, "w") as f:
            f.write(testbench_code)

        # Step 3: Review
        if progress_cb:
            progress_cb(50 + attempt * 20, "Reviewing testbench quality...")

        review = review_testbench(physiology, testbench_code, api_key)

        review_path = workspace / f"mark2_review_{attempt}.json"
        with open(review_path, "w") as f:
            json.dump(review, f, indent=2)

        if progress_cb:
            progress_cb(60 + attempt * 20, f"Review score: {review.get('score', 0)}/100")

        if review.get("passed", False):
            best_code = testbench_code
            best_review = review
            break

        # Store best attempt so far
        if best_review is None or review.get("score", 0) > best_review.get("score", 0):
            best_code = testbench_code
            best_review = review

    # Save the best testbench
    if best_code:
        final_tb_path = workspace / "ai_testbench.py"
        with open(final_tb_path, "w") as f:
            f.write(best_code)

    result = {
        "physiology": physiology,
        "review": best_review,
        "testbench_path": str(workspace / "ai_testbench.py") if best_code else None,
        "ports": ports,
        "iterations": 1 if best_review and best_review.get("passed", False) else MAX_RETRIES,
        "passed": best_review.get("passed", False) if best_review else False
    }

    if progress_cb:
        progress_cb(100, "Pipeline complete")

    return result
