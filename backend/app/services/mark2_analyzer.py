"""Mark 2 — Semantic Analyzer Agent
Uses DeepSeek to understand the design intent and produce a Circuit Physiology Document."""

import json
import requests
from typing import Optional

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

ANALYZER_PROMPT = """You are a senior digital design engineer. Analyze the following HDL code and produce a detailed "Circuit Physiology Document" in JSON format.

Identify:
1. What type of circuit this is (DSP filter, FSM, ALU, memory, barrel shifter, multiplier, etc.)
2. The role of each port (clock, data input, data output, control, reset, etc.)
3. The expected input stimulus type for each port (random, sine wave, boundary values, sequential pattern, state transitions, etc.)
4. Recommended test scenarios with cycle counts
5. Clock configuration (if any)
6. Any specific timing or protocol requirements

HDL CODE:
```verilog
{hdl_code}
```

PORT INFO (from synthesis):
{port_info}

Return ONLY valid JSON with this exact structure, no markdown:
{{
  "design_type": "string describing the circuit",
  "design_summary": "one-line summary of what this circuit does",
  "ports": [{{"name": "port_name", "direction": "input/output", "width": N, "role": "clock/reset/data/control/status", "stimulus_type": "random/sine/boundary/sequential/state_transition/pattern"}}],
  "test_scenarios": [{{"name": "scenario_name", "description": "what this tests", "cycles": N, "ports_to_vary": ["port1", "port2"]}}],
  "clock_info": {{"exists": true/false, "name": "clk_name", "frequency_hz": N, "active_edge": "rising/falling"}},
  "reset_info": {{"exists": true/false, "name": "rst_name", "active_level": "high/low", "assert_cycles": N}},
  "evaluation_metrics": ["metric1", "metric2"]
}}"""

def analyze_design(hdl_code: str, port_info: list, api_key: str, timeout: int = 60) -> dict:
    if not api_key:
        raise ValueError("DeepSeek API key not configured")

    port_str = json.dumps(port_info, indent=2) if port_info else "No port info available"
    prompt = ANALYZER_PROMPT.format(hdl_code=hdl_code[:32000], port_info=port_str)

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a senior digital design engineer. Output ONLY valid JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 4096
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

        result = json.loads(content)

        # Validate structure
        if "design_type" not in result:
            result["design_type"] = "unknown"
        if "ports" not in result:
            result["ports"] = port_info if port_info else []
        if "test_scenarios" not in result:
            result["test_scenarios"] = [{"name": "default", "description": "Standard operation", "cycles": 100}]

        return result

    except requests.exceptions.Timeout:
        raise TimeoutError("DeepSeek API timed out")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise PermissionError("Invalid DeepSeek API key")
        raise RuntimeError(f"DeepSeek API error: {e.response.status_code}")
    except json.JSONDecodeError:
        raise RuntimeError("Failed to parse DeepSeek response as JSON")
    except Exception as e:
        raise RuntimeError(f"Analysis failed: {e}")
