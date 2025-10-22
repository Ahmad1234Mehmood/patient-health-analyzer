# Patient Health Data Analyzer

A full-stack medical data processing workbench: 12-lead ECG signal analysis (Butterworth filtering, FFT, autocorrelation, R-peak detection, HRV) and chest X-ray image processing (CLAHE, Canny / Sobel edge detection, lung segmentation) with quantitative validation against expert segmentation masks.

## Tech stack

**Backend:** Python · Flask · NumPy · SciPy · OpenCV · WFDB (PhysioNet)
**Frontend:** React 18 · Vite · Tailwind · Recharts
**Data:** PhysioNet 12-lead ECG (500 Hz, CC BY 4.0) · Montgomery County TB chest X-rays with expert lung masks (CC BY 4.0)

## Features

- **ECG Lab** - pick a record + lead, tune the Butterworth band-pass / notch live, and see: raw vs filtered signal with R-peaks · Welch PSD + FFT + band power · autocorrelation · RR tachogram & Poincaré · ensemble-average beat · 12-lead table · filter Bode plot · signal-quality score.
- **X-ray Lab** - every pipeline stage visible (Original → CLAHE → Sobel → Canny → mask → overlay), 3 segmentation methods, lung measurements, histogram, ground-truth contour + Dice/IoU/HD95 when a mask exists.
- **Validation** - batch evaluation on every image with a mask; Dice histogram, per-image table, method comparison.
- **Datasets** - what is loaded, and one-command import of real data.
- **PDF reports** (jsPDF) for any ECG or X-ray analysis, **history** of saved analyses (SQLite), **dark / light theme**, file **uploads** (WFDB `.hea+.dat`, CSV, NPY, NPZ, PNG, JPG).

## Quick start

**Needs:** Python 3.10-3.13, Node.js 18+ (20/22 recommended). No GPU. No API keys. Detailed guide with troubleshooting: [`docs/SETUP_GUIDE.md`](docs/SETUP_GUIDE.md).

### Option A - one command (recommended)

| OS | Command (from the project root) |
|---|---|
| Windows | double-click `run_windows.bat` (or run it in a terminal) |
| macOS / Linux | `bash run.sh` |

It creates a virtual environment, installs everything, generates sample data and starts both servers. Open **http://localhost:5173**.

### Option B - manual (two terminals)

```bash
# Terminal 1 - backend
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
python run.py                      # → http://localhost:5000

# Terminal 2 - frontend
cd frontend
npm install
npm run dev                        # → http://localhost:5173
```

### Option C - production-style (single port)

```bash
cd frontend && npm install && npm run build      # creates frontend/dist
cd ../backend && python run.py                   # Flask now serves the React app too → http://localhost:5000
```

### Option D - Docker

```bash
docker compose up --build        # → http://localhost:5000
```

## Data sources

See [`docs/DATASETS.md`](docs/DATASETS.md) for full instructions. Short version:

```bash
cd backend
# ECG: copy your PhysioNet .hea/.dat pairs into data/ecg/   (or download open PTB-XL records)
python scripts/fetch_physionet_ecg.py --n 28 --clear-synthetic

# Chest X-ray: Montgomery images + merged lung masks
python scripts/prepare_montgomery.py --src /path/to/MontgomerySet --clear-synthetic
# MIMIC-CXR (credentialed access): copy chosen JPG/PNG files into data/xray/images/
```

## Licence

Code: MIT. Data: PhysioNet (PTB-XL, MIMIC-CXR - credentialed), NIH/NLM Montgomery County TB set - follow each dataset's licence and citation requirements.


