# 🧠 GateScan Mark 2 — Cognitive Behavioral Engine

**بازوی ارزیابی رفتاری شناختی — Multi-Agent Fault Injection Platform**

Mark 2 represents a leap from blind statistical testing (Mark 1) to **intelligent behavioral verification**. It uses a **Actor-Critic architecture** with **DeepSeek LLM agents** to understand HDL designs, generate targeted testbenches, and verify them automatically — all before injecting stuck-at faults.

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        USER HDL CODE                              │
│                    (.v / .sv / .vhd / .vhdl)                      │
└──────────────────────────┬───────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ ① Semantic Analyzer Agent 🔍                                    │
│                                                                  │
│ Model: DeepSeek (large context)                                  │
│ Input: Raw HDL + netlist JSON                                    │
│ Task: Discover design intent — what does this circuit DO?        │
│       Is it a DSP filter? FSM? ALU? Barrel shifter?              │
│ Output: "Circuit Physiology Document" (JSON)                     │
│   - design_type, port roles, expected behavior                   │
│   - test scenarios, clock/reset info, evaluation metrics         │
└──────────────────────┬───────────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ ② Actor Agent (Generator) 🎭                                    │
│                                                                  │
│ Model: DeepSeek (code generation)                                │
│ Input: Circuit Physiology Document                               │
│ Task: Generate a complete cocotb testbench with MEANINGFUL       │
│       stimuli instead of random vectors:                         │
│       - DSP filters → sine waves, impulse responses              │
│       - ALUs → boundary values, arithmetic sequences             │
│       - FSMs → state transition sequences                        │
│       - Shifters → exhaustive shift patterns                     │
│ Output: Python cocotb testbench file (`ai_testbench.py`)         │
└──────────────────────┬───────────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ ③ Critic Agent (Reviewer) ✅                                    │
│                                                                  │
│ Model: DeepSeek (reasoning)                                      │
│ Input: Original HDL + Generated testbench                        │
│ Task: QA review — check bit-widths, clock setup, stimulus        │
│       quality, syntax validity                                   │
│ Output: Review Report (JSON) with score 0-100                   │
│   Auto-retry: if score < 70, loops back to Actor (max 2 tries)  │
└──────────────────────┬───────────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ ④ Execution Hub ⚡                                               │
│                                                                  │
│ Infrastructure: GLFI Engine (Icarus Verilog + Cocotb)            │
│ Task: Execute the verified AI testbench                          │
│       Apply stuck-at faults on flattened netlist                 │
│       Report masked vs propagated cycles per gate                │
│ Output: CSV fault report                                         │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Upload & Synthesize
Upload your `.v` / `.sv` / `.vhd` / `.vhdl` files and run synthesis as before.

### 2. Run Mark 2 Pipeline
Enter your **DeepSeek API key** and click **Run Mark 2 Pipeline**.

The three agents execute sequentially:
```
🔍 Analyzing... → 🎭 Generating... → ✅ Reviewing...
```

### 3. Review Results
- **Circuit Physiology Document** — what the AI determined about your design
- **Generated Testbench** — the cocotb code with meaningful stimuli
- **Review Score** — quality score (0-100) with per-check breakdown

### 4. Run Fault Injection
Click **Run GLFI** — the verified AI testbench drives the simulation instead of random vectors.

---

## 🧬 Agent Details

### Semantic Analyzer
```json
{
  "design_type": "barrel_shifter",
  "design_summary": "8-bit barrel shifter with 3-bit select",
  "ports": [
    {"name": "din", "direction": "input", "width": 8, "role": "data", "stimulus_type": "pattern"},
    {"name": "sel", "direction": "input", "width": 3, "role": "control", "stimulus_type": "sequential"},
    {"name": "dout", "direction": "output", "width": 8, "role": "data", "stimulus_type": ""}
  ],
  "test_scenarios": [
    {"name": "full_range_shift", "description": "Shift all bits through all positions", "cycles": 64},
    {"name": "boundary_sel", "description": "Test min/max select values", "cycles": 16}
  ]
}
```

### Actor — Generated Stimuli
Instead of random: `{din: random.randint(0, 255), sel: random.randint(0, 7)}`
The Actor produces targeted patterns:
```python
for shift in range(8):
    for bit in range(8):
        vec = {"din": 1 << bit, "sel": shift}
        stimuli.append(vec)
```

### Critic — Review Format
```json
{
  "score": 92,
  "passed": true,
  "port_check": {"status": "pass", "issues": []},
  "clock_check": {"status": "pass", "issues": []},
  "stimulus_check": {"status": "pass", "issues": ["Only 50 cycles for 64 required"]}
}
```

---

## 🔧 API Reference

### Run Full Pipeline
```
POST /api/mark2/run
Body:  session_id, top_module, api_key
Return: { "task_id": "mark2_xxx", "status": "processing" }
```

### Check Status
```
GET /api/mark2/status/{task_id}
```

### Get Results
```
GET /api/mark2/physiology/{session_id}
GET /api/mark2/testbench/{session_id}
GET /api/mark2/review/{session_id}
```

### Quick Run (no polling)
```
POST /api/mark2/quick-run
Body:  session_id, top_module, api_key
Return: Full pipeline result inline
```

---

## 🛠 Tech Stack

| Component | Technology |
|---|---|
| Agents | **DeepSeek** (deepseek-chat) |
| Backend | FastAPI + Python 3.13 |
| Synthesis | Yosys 0.52 + GHDL 5.0 |
| Simulation | Icarus Verilog 12 + Cocotb 2.0 |
| Frontend | React 18 + Tailwind CSS v4 |
| SVG | Graphviz + custom beautifier |
| Auth | DeepSeek API key (user-provided, per-session) |

---

## 📝 License

MIT License — see [LICENSE](LICENSE)

---

*"From blind vectors to intelligent verification."*
