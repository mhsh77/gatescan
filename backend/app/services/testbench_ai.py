import requests
import json
import time
from typing import List, Dict, Optional

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

def generate_test_vectors(
    hdl_code: str,
    top_module: str,
    ports: List[Dict],
    sim_cycles: int = 100,
    api_key: str = ""
) -> Optional[List[Dict]]:
    """Generate meaningful test vectors using DeepSeek AI.

    Args:
        hdl_code: The user's VHDL/Verilog source code
        top_module: Name of the top-level module
        ports: List of port dicts with name, direction, width
        sim_cycles: Number of test vectors to generate
        api_key: DeepSeek API key

    Returns:
        List of dicts, each with port_name: value mappings, or None on failure
    """
    if not api_key:
        raise ValueError("DeepSeek API key not configured")

    port_desc = "\n".join([
        f"  - {p['name']} ({p['direction']}, width={p['width']})"
        for p in ports
    ])

    prompt = f"""You are an expert hardware verification engineer. Generate test vectors for the following digital design.

TOP MODULE: {top_module}

PORTS:
{port_desc}

HDL CODE:
```verilog
{hdl_code}
```

Generate exactly {sim_cycles} test vectors as a JSON array. Each vector should be an object mapping port names to integer values.
Cover these scenarios:
1. Reset / initial state
2. Normal operation with typical inputs
3. Boundary values (min, max, edges)
4. Corner cases
5. Random meaningful combinations

IMPORTANT: Only include INPUT ports. Output ports will be captured by the simulator.
Return ONLY valid JSON, no markdown, no explanation. Format:
[{{"port_name": value, ...}}, ...]
"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": "You are a hardware verification engineer. You output only valid JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 16000
    }

    try:
        resp = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        # Clean markdown code blocks if present
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        content = content.strip()

        vectors = json.loads(content)
        if not isinstance(vectors, list):
            raise ValueError("Response is not a list")

        return vectors[:sim_cycles]

    except requests.exceptions.Timeout:
        raise TimeoutError("DeepSeek API timed out after 60 seconds")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise PermissionError("Invalid DeepSeek API key")
        raise RuntimeError(f"DeepSeek API error: {e.response.status_code}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse DeepSeek response as JSON: {e}")
    except Exception as e:
        raise RuntimeError(f"AI testbench generation failed: {e}")


def analyze_hdl_ports(hdl_code: str, top_module: str) -> List[Dict]:
    """Simple port extraction from HDL code (fallback if not provided)."""
    import re
    ports = []
    in_module = False

    for line in hdl_code.split("\n"):
        stripped = line.strip()

        # Verilog module declaration
        m = re.search(rf'module\s+{re.escape(top_module)}\s*\(', stripped)
        if m:
            in_module = True
            continue

        if in_module and ";" in stripped and "endmodule" not in stripped:
            # Port declarations
            pm = re.search(r'(input|output|inout)\s*(wire|reg|logic)?\s*(\[.*?\])?\s*(\w+)', stripped)
            if pm:
                direction = pm.group(1)
                width_str = pm.group(3)
                name = pm.group(4)
                # Parse width
                if width_str:
                    wm = re.search(r'(\d+):(\d+)', width_str)
                    if wm:
                        width = abs(int(wm.group(1)) - int(wm.group(2))) + 1
                    else:
                        width = 1
                else:
                    width = 1
                ports.append({"name": name, "direction": direction, "width": width})

        if "endmodule" in stripped:
            break

    return ports
