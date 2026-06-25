"""Mark 2 — Critic Agent (Testbench Reviewer)
Uses DeepSeek to review the generated testbench for correctness."""

import json
import requests
from typing import Optional

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

CRITIC_PROMPT = """You are a senior QA engineer for hardware verification. Review the following cocotb testbench for a {design_type} design.

ORIGINAL HDL PORTS:
{ports}

GENERATED TESTBENCH CODE:
```python
{testbench_code}
```

Review the testbench for these specific criteria:
1. PORT COMPATIBILITY: Do the port names and widths in the testbench match the original design? Check every port.
2. CLOCK SETUP: Is the clock configured correctly (frequency, edge, polarity)?
3. RESET HANDLING: Is reset properly asserted and de-asserted?
4. STIMULUS QUALITY: Are the generated stimuli meaningful for this design type?
5. BIT WIDTHS: Are all signal assignments within valid bit width ranges?
6. SYNTAX: Is the Python code syntactically valid?

Return ONLY a JSON object with this exact structure:
{{
  "score": 85,
  "passed": true,
  "port_check": {{"status": "pass/fail", "issues": []}},
  "clock_check": {{"status": "pass/fail", "issues": []}},
  "reset_check": {{"status": "pass/fail", "issues": []}},
  "stimulus_check": {{"status": "pass/fail", "issues": []}},
  "width_check": {{"status": "pass/fail", "issues": []}},
  "syntax_check": {{"status": "pass/fail", "issues": []}},
  "summary": "Overall assessment",
  "suggestions": ["suggestion1", "suggestion2"]
}}

SCORE THRESHOLD: 70. Below 70 = failed review."""

def review_testbench(physiology: dict, testbench_code: str, api_key: str, timeout: int = 60) -> dict:
    if not api_key:
        raise ValueError("DeepSeek API key not configured")

    ports_str = json.dumps(physiology.get("ports", []), indent=2)

    prompt = CRITIC_PROMPT.format(
        design_type=physiology.get("design_type", "unknown"),
        ports=ports_str,
        testbench_code=testbench_code
    )

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a senior QA engineer. Output ONLY valid JSON."},
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

        if "score" not in result:
            result["score"] = 50
            result["passed"] = False

        result["passed"] = result.get("score", 0) >= 70

        return result

    except requests.exceptions.Timeout:
        raise TimeoutError("DeepSeek API timed out during review")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise PermissionError("Invalid DeepSeek API key")
        raise RuntimeError(f"DeepSeek API error: {e.response.status_code}")
    except json.JSONDecodeError:
        raise RuntimeError("Failed to parse review response as JSON")
    except Exception as e:
        raise RuntimeError(f"Review failed: {e}")
