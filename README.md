# Patient Health Data Analyzer

A full-stack web application for medical signal and image analysis: 12-lead **ECG signal processing** (Butterworth filtering, FFT, autocorrelation, R-peak detection, HRV) and **chest X-ray image processing** (CLAHE, Canny/Sobel edge detection, lung segmentation) with quantitative validation against expert segmentation masks.

**Stack:** Python · Flask · NumPy · SciPy · OpenCV · WFDB · React 18 · Vite · Tailwind · Recharts  
**Data:** 28 ECG recordings — Norwegian Endurance Athlete ECG Database (PhysioNet, CC BY 4.0) · 138 chest X-rays — Montgomery County TB dataset with expert lung masks (CC BY 4.0)

---

## Features

- **ECG Lab** — pick a record and lead, tune the Butterworth band-pass / notch live, and see: raw vs filtered signal with R-peaks · Welch PSD + FFT + band power · autocorrelation · RR tachogram & Poincaré · ensemble-average beat · 12-lead table · filter Bode plot · signal-quality score
- **X-ray Lab** — every pipeline stage visible (Original → CLAHE → Sobel → Canny → mask → overlay), 3 segmentation methods, lung measurements, histogram, ground-truth contour + Dice/IoU/HD95
- **Validation** — batch evaluation on every image with a mask; Dice histogram, per-image table, method comparison
- **PDF reports** (jsPDF), history of saved analyses (SQLite), dark/light theme, file uploads (WFDB `.hea+.dat`, CSV, NPY, NPZ, PNG, JPG)

---

## Architecture

```
 ┌──────────────── React 18 + Vite (port 5173) ────────────────┐
 │  Dashboard │ ECG Lab │ X-ray Lab │ Validation │ History     │
 └───────────────────────────┬─────────────────────────────────┘
                             │ JSON / multipart
 ┌───────────────────────────▼─────────────────────────────────┐
 │              Flask API  (port 5000)  /api/v1                │
 ├───────────────────────────┬─────────────────────────────────┤
 │  services/ecg             │  services/xray                  │
 │  filters  (Butterworth)   │  preprocess (CLAHE)             │
 │  rpeaks   (Pan-Tompkins)  │  edges (Sobel, Canny)           │
 │  spectral (FFT, Welch)    │  segmentation (Otsu/kmeans/…)   │
 │  autocorr · hrv · quality │  metrics (Dice, IoU, HD95)      │
 └───────────────────────────┴─────────────────────────────────┘
        data/ecg/*.hea,.dat        data/xray/images + masks
```

---

## Quick start

**Requirements:** Python 3.10–3.13, Node.js 18+. No GPU. No API keys.

```bash
# Terminal 1 — backend
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py                    # → http://localhost:5000

# Terminal 2 — frontend
cd frontend
npm install
npm run dev                      # → http://localhost:5173
```

Or on Windows double-click `run_windows.bat` to do everything in one step.

---

## Data sources

**ECG** — 28 twelve-lead recordings at 500 Hz are bundled in `backend/data/ecg/`.  
Source: Norwegian Endurance Athlete ECG Database, PhysioNet, CC BY 4.0.

**Chest X-ray** — 138 chest X-rays with expert lung masks from the Montgomery County TB dataset (CC BY 4.0).  
Download `Montgomery.zip` from [Mendeley Data](https://data.mendeley.com/datasets/8gf9vpkhgy/2) and run:

```bash
cd backend
python scripts/import_real_data.py xray --src /path/to/Montgomery --max 138 --clear-synthetic
```

---

## Project structure

```
patient-health-analyzer/
├── backend/
│   ├── app/
│   │   ├── routes/          # health · datasets · ecg · xray · history
│   │   └── services/
│   │       ├── ecg/         # filters · rpeaks · spectral · autocorr · hrv · quality · analyzer
│   │       └── xray/        # preprocess · edges · segmentation · metrics · analyzer
│   ├── scripts/             # import_real_data.py · evaluate_ecg.py · evaluate_segmentation.py
│   ├── tests/               # 24 pytest tests: DSP, API, segmentation
│   └── data/                # ecg/ · xray/images · xray/masks
├── frontend/
│   └── src/
│       ├── pages/           # Dashboard · EcgLab · XrayLab · Validation
│       └── components/      # Layout · Sidebar · charts · ui
└── docs/
    ├── SETUP_GUIDE.md
    └── DATASETS.md
```

---

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | liveness |
| GET | `/api/v1/ecg/records` | list ECG records |
| POST | `/api/v1/ecg/analyze` | full ECG analysis |
| GET | `/api/v1/xray/images` | list X-ray images |
| POST | `/api/v1/xray/analyze` | full X-ray analysis |
| GET | `/api/v1/xray/evaluate` | batch Dice/IoU/HD95 |
| GET | `/api/v1/history` | saved analyses |

---

## Licence

Code: MIT.  
Data: Norwegian Endurance Athlete ECG Database (PhysioNet, CC BY 4.0) · Montgomery County TB Chest X-ray Set (NIH/NLM, CC BY 4.0).