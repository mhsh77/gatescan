"""Mark 2 — Actor Agent (Testbench Generator)
Uses DeepSeek to generate a targeted cocotb testbench based on the Circuit Physiology Document."""

import json
import requests
from typing import Optional

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

ACTOR_PROMPT = """You are an expert hardware verification engineer. Generate a complete Python cocotb testbench file based on the following "Circuit Physiology Document".

THE DESIGN IS A: {design_type}
SUMMARY: {summary}

CIRCUIT PORTS:
{ports}

TEST SCENARIOS TO IMPLEMENT:
{scenarios}

CLOCK INFO: {clock_info}
RESET INFO: {reset_info}

ORIGINAL HDL CODE (for reference):
```verilog
{hdl_code}
```

Generate a COMPLETE, SELF-CONTAINED Python file that can be used as a cocotb testbench. The file MUST:

1. Import cocotb and necessary triggers (RisingEdge, Timer, Clock)
2. Define a function `generate_stimuli()` that returns a list of dictionaries. Each dict maps port names to integer values for one simulation cycle.
3. Generate MEANINGFUL stimuli based on the design type:
   - For DSP/filters: generate sine waves, impulse responses, step functions
   - For ALUs: generate arithmetic sequences, boundary values, edge cases
   - For FSMs: generate state transition sequences
   - For shifters/multipliers: generate input patterns that exercise all paths
   - For memory: generate address sweep patterns
4. Define a cocotb test function `run_ai_testbench(dut)` that:
   a. Sets up clock if needed
   b. Applies the stimuli cycle by cycle
   c. Captures output values
   d. Returns the stimuli list via module-level variable `GENERATED_STIMULI`
5. Handle reset properly if it exists

The stimuli must be stored in a module-level variable `GENERATED_STIMULI = []` so the orchestrator can access them.

IMPORTANT: Output ONLY the Python code. No markdown, no explanation. The code must be syntactically valid Python 3.

TEMPLATE:
```python
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer
import math

GENERATED_STIMULI = []

def generate_stimuli():
    # ... generate vectors
    return vectors

@cocotb.test()
async def run_ai_testbench(dut):
    global GENERATED_STIMULI
    stimuli = generate_stimuli()
    GENERATED_STIMULI = stimuli
    # ... apply stimuli
```

Now write the complete Python code:"""

def generate_testbench(physiology: dict, hdl_code: str, api_key: str, timeout: int = 120) -> str:
    if not api_key:
        raise ValueError("DeepSeek API key not configured")

    ports_str = json.dumps(physiology.get("ports", []), indent=2)
    scenarios_str = json.dumps(physiology.get("test_scenarios", []), indent=2)
    clock_info = json.dumps(physiology.get("clock_info", {}))
    reset_info = json.dumps(physiology.get("reset_info", {}))

    prompt = ACTOR_PROMPT.format(
        design_type=physiology.get("design_type", "unknown"),
        summary=physiology.get("design_summary", "Digital circuit"),
        ports=ports_str,
        scenarios=scenarios_str,
        clock_info=clock_info,
        reset_info=reset_info,
        hdl_code=hdl_code[:32000]
    )

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are an expert hardware verification engineer. Output ONLY valid Python code, no markdown."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 8192
    }

    try:
        resp = requests.post(DEEPSEEK_URL, json=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            content = content.rsplit("```", 1)[0] if "```" in content else content
            content = content.strip()

        if "import cocotb" not in content:
            content = "import cocotb\nfrom cocotb.clock import Clock\nfrom cocotb.triggers import RisingEdge, FallingEdge, Timer\nimport math\n\nGENERATED_STIMULI = []\n\n" + content

        return content

    except requests.exceptions.Timeout:
        raise TimeoutError("DeepSeek API timed out generating testbench")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise PermissionError("Invalid DeepSeek API key")
        raise RuntimeError(f"DeepSeek API error: {e.response.status_code}")
    except Exception as e:
        raise RuntimeError(f"Testbench generation failed: {e}")
