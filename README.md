# GateScan ⚡

**Fault Injection Scanner for FPGA & ASIC Designs**

GateScan is an online platform that synthesizes VHDL/Verilog designs and performs automated **stuck-at fault injection campaigns** to identify vulnerable gates in your digital circuits. Upload your design, run synthesis, and discover which faults propagate to outputs — all through a web browser.

---

## Features

| Feature | Description |
|---|---|
| **HDL Synthesis** | Upload `.v`, `.sv`, `.vhd`, `.vhdl` files — Yosys + GHDL pipeline |
| **RTL Schematic** | Color-coded SVG schematic with legend (AND=green, OR=blue, NOT=red, MUX=purple, DFF=orange) |
| **PNG Export** | One-click conversion from SVG to PNG via `rsvg-convert` |
| **Fault Injection** | Automatically injects stuck-at-0 / stuck-at-1 faults on every gate |
| **Fault Metrics** | Per-gate report: masked cycles, propagated cycles, vulnerable status |
| **CSV Reports** | Download detailed campaign results |
| **Real-time Progress** | Live Yosys pass stream + GLFI stage tracking via polling API |
| **Async Processing** | Long-running tasks run in background threads — no timeouts |

## Architecture

```
┌─────────────┐     ┌─────────────────────────────────────┐     ┌──────────┐
│  React SPA  │────▶│         FastAPI Backend              │────▶│  Yosys   │
│  Tailwind   │     │  /api/synthesis/run                  │     │  GHDL    │
│  (port 80)  │     │  /api/synthesis/status/{task_id}     │     │  Icarus  │
│             │     │  /api/glfi/run                       │     │  cocotb  │
│             │     │  /api/glfi/status/{task_id}          │     └──────────┘
│             │     │  /api/sessions/{id}/{file}           │
│             │     │  /api/health                         │
└─────────────┘     └─────────────────────────────────────┘
```

## Quick Start

### Using the hosted instance

```
http://154.91.170.5:8080
```

1. Upload your `.v` / `.sv` / `.vhd` / `.vhdl` files
2. Enter the **top module name** (the actual module in your code, not the filename)
3. Select output formats (Verilog netlist, JSON netlist, RTL schematic)
4. Click **Run Synthesis** — watch Yosys passes stream in real-time
5. Set simulation cycles and click **Run Fault Injection**
6. Download the CSV report with per-gate fault metrics

### Running locally

```bash
# Clone the repo
git clone https://github.com/mhsh77/gatescan.git
cd gatescan

# Backend
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8080

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### Docker

```bash
docker build -t gatescan -f docker/Dockerfile .
docker run -p 8080:8080 gatescan
```

## API Reference

### Health Check

```
GET /api/health
```

### Synthesis

```
POST /api/synthesis/run

Body (multipart/form-data):
  files[]     - HDL files (.v, .sv, .vhd, .vhdl)
  top_module  - Name of the top-level module (string)
  outputs     - Comma-separated: verilog,json,svg (default: verilog,json,svg)

Response: { "task_id": "task_abc123", "status": "processing" }
```

```
GET /api/synthesis/status/{task_id}

Response:
{
  "status": "completed" | "processing" | "failed",
  "overall_progress": 87,
  "detail": "Yosys: 3.5. Executing OPT_EXPR pass",
  "yosys_passes": ["..."],
  "result": {
    "session_id": "session_abc123",
    "results": {
      "verilog": "/workspaces/session_abc123/netlist.v",
      "json":   "/workspaces/session_abc123/netlist.json",
      "svg":    "/workspaces/session_abc123/schematic.svg"
    }
  }
}
```

### Fault Injection

```
POST /api/glfi/run

Body (multipart/form-data):
  session_id  - Session ID from synthesis
  top_module  - Top module name
  sim_cycles  - Number of simulation cycles (default: 1000)

Response: { "task_id": "glfi_session_abc123", "status": "processing" }
```

```
GET /api/glfi/status/{task_id}

Response:
{
  "status": "completed",
  "overall_progress": 100,
  "detail": "Campaign complete",
  "result": {
    "message": "Fault campaign completed for 1000 cycles.",
    "data": {
      "results_csv": "/workspaces/session_abc123/campaign_results.csv",
      "total_faults": 122,
      "vulnerable": 45,
      "masked": 77
    }
  }
}
```

### File Download

```
GET /api/sessions/{session_id}/netlist.v
GET /api/sessions/{session_id}/netlist.json
GET /api/sessions/{session_id}/schematic.svg
GET /api/sessions/{session_id}/schematic.png
GET /api/sessions/{session_id}/campaign_results.csv
```

## CSV Report Format

```
Target_ID,Net_Name,Zone,Fault_Type,Masked_Cycles,Propagated_Cycles,Status
1,y,COMB_CLOUD,SA0,60,40,Vulnerable
1,y,COMB_CLOUD,SA1,58,42,Vulnerable
```

| Column | Description |
|---|---|
| `Target_ID` | Unique gate identifier |
| `Net_Name` | Output net name of the gate |
| `Zone` | `COMB_CLOUD` (combinational) or `STATE_MEMORY` (sequential) |
| `Fault_Type` | `SA0` (stuck-at-0) or `SA1` (stuck-at-1) |
| `Masked_Cycles` | Cycles where the fault did NOT propagate to any output |
| `Propagated_Cycles` | Cycles where the fault DID propagate to an output |
| `Status` | `Masked` (100% masked) or `Vulnerable` (some propagation) |

## Dependencies

### Backend
- **Python 3.11+** — FastAPI, uvicorn, pydantic, cocotb
- **Yosys 0.52+** — Verilog synthesis and technology mapping
- **GHDL 5.0+** — VHDL analysis and Verilog conversion
- **Icarus Verilog 12+** — Simulation backend for cocotb
- **librsvg2** — SVG-to-PNG conversion

### Frontend
- **React 18** + **Tailwind CSS v4** — Built with Vite

## SVG Color Legend

When you enable the RTL Schematic output, the generated SVG includes a color legend:

| Color | Cell Type |
|---|---|
| 🟢 Green | AND / ANDNOT |
| 🔵 Blue | OR / ORNOT |
| 🔴 Red | NOT (Inverter) |
| 🟣 Purple | MUX |
| 🟠 Orange | DFF (Flip-flop) |
| ⚫ Dark Slate | I/O Port |

## License

MIT License — see [LICENSE](LICENSE) for details.

---

Built with ❤️ for the open-source hardware community.
