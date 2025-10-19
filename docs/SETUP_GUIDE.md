# Setup & Run Guide (step by step)

Works on Windows 10/11, macOS and Linux. No GPU, no API keys, no database server.

## 0. What you need installed

| Tool | Version | Check | Download |
|---|---|---|---|
| Python | 3.10 - 3.13 | `python --version` (Windows: `py -3 --version`) | python.org (tick **Add to PATH** on Windows) |
| Node.js + npm | 18+ (20/22 best) | `node --version` · `npm --version` | nodejs.org (LTS) |
| (optional) Git | any | `git --version` | git-scm.com |
| (optional) Docker Desktop | any | `docker --version` | docker.com |

## 1. Unzip

Unzip `patient-health-analyzer.zip` somewhere without spaces if possible (e.g. `C:\dev\patient-health-analyzer` or `~/dev/...`). Open a terminal **in that folder** (VS Code: *File → Open Folder*, then *Terminal → New Terminal*).

## 2A. Fastest path - one command

- **Windows:** `run_windows.bat`
- **macOS/Linux:** `bash run.sh`

The first run takes 2-5 minutes (downloads Python + npm packages). When it prints that both servers are up, open **http://localhost:5173**.

## 2B. Manual path

### Backend
```bash
cd backend
python -m venv .venv
# activate:
#   Windows (PowerShell):  .venv\Scripts\Activate.ps1
#   Windows (cmd):         .venv\Scripts\activate.bat
#   macOS / Linux:         source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # Windows: copy .env.example .env
python run.py
```
You should see `generated 28 synthetic 12-lead ECG records…` (first run only) and `Running on http://127.0.0.1:5000`.
Check: open http://localhost:5000/health → `{"status":"healthy",…}`.

### Frontend (second terminal)
```bash
cd frontend
npm install
npm run dev
```
Open **http://localhost:5173**. The top-right pill must say **API online**.

## 3. Tour (10 minutes)

1. **Dashboard** - system status, quick-look ECG and X-ray.
2. **ECG Lab** → pick `SYN-ECG-006` ("heavy noise") → switch off *Butterworth band-pass* and watch the signal degrade → switch on again. Open *Spectrum (FFT)*: the 50 Hz line disappears when *Notch* is on. Open *Autocorrelation*, *HRV*, *Filter design*.
3. **X-ray Lab** → try `otsu` vs `kmeans`; change *Morphology kernel*; press *All stages*. Press **PDF report**.
4. **Validation** → *Compare all methods*.
5. **Datasets** → how to load real data.

## 4. Run the tests
```bash
cd backend
python -m pytest -q
```

## 5. Production-style single port
```bash
cd frontend && npm run build
cd ../backend && python run.py          # http://localhost:5000 serves API + UI
```
Linux/macOS server: `gunicorn -w 2 -b 0.0.0.0:5000 --timeout 300 wsgi:app` · Windows server: `waitress-serve --port=5000 wsgi:app`.

## 6. Docker
```bash
docker compose up --build
```
Open http://localhost:5000. Real data: put it in `backend/data/…` on your machine (mounted as a volume).

## 7. Troubleshooting

| Problem | Fix |
|---|---|
| `python` not found (Windows) | use `py -3`, or reinstall Python with *Add to PATH* |
| PowerShell: "running scripts is disabled" when activating the venv | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` or use `cmd` + `activate.bat` |
| `pip install` fails building a package | upgrade pip (`python -m pip install -U pip`); use Python 3.10-3.13 (very new/old versions may lack wheels) |
| Pill says **API offline** | backend not running or wrong port → start `python run.py`; check `frontend/.env` → `VITE_BACKEND_URL` |
| Port 5000 busy (macOS AirPlay uses it) | set `BACKEND_PORT=5001` in `backend/.env` **and** `VITE_BACKEND_URL=http://localhost:5001` in `frontend/.env` |
| Port 5173 busy | `npm run dev -- --port 5180` and set `FRONTEND_URL=http://localhost:5180` in `backend/.env` |
| CORS error in the browser console | `FRONTEND_URL` in `backend/.env` must equal the address in your browser |
| Empty record/image lists | `python scripts/generate_synthetic_data.py --force` or see `docs/DATASETS.md` |
| `Could not read WFDB record` | both `.hea` and `.dat` must be present, same stem, and the `.hea` must name the right `.dat` |
| Validation is slow | normal on 138 full-resolution Montgomery PNGs (≈1-2 min); results are cached |
| Blank page after `npm run build` | run the backend from `backend/` so `../frontend/dist` resolves, or set `FRONTEND_DIST` |
| Icons show as words | fonts load from `node_modules` - run `npm install` again |

## 8. Where to change things
| I want to… | Edit |
|---|---|
| change default filter cut-offs | `frontend/src/pages/EcgLab.jsx` (`DEFAULTS`) and `backend/app/services/ecg/analyzer.py` (`ECGParams`) |
| add a segmentation method | `backend/app/services/xray/segmentation.py` (`_candidate`, `METHODS`) + button in `XrayLab.jsx` |
| re-theme the UI | `frontend/src/index.css` (variables) |
| add an API endpoint | new file in `backend/app/routes/` + `register_blueprint` in `app/__init__.py` |


