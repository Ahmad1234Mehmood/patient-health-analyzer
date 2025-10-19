# Datasets - how to plug in the real data

The app ships with **synthetic** demo data (generated on first run, clearly labelled `synthetic`) so you can run everything immediately. Real data uses the *same* code path - just put files in the right folders.

```
backend/data/
├── ecg/             *.hea + *.dat  (WFDB pairs)   or  *.npz
└── xray/
    ├── images/      *.png / *.jpg                 (chest X-rays)
    └── masks/       <same name>.png               (binary lung mask - optional)
```

The **Datasets** page in the app shows what was detected (counts, `real / synthetic / mixed`).

---

## 1. ECG - PhysioNet 12-lead @ 500 Hz

Your CV: *"28 twelve-lead ECG recordings at 500 Hz"*.

**Format - WFDB.** Each recording = two files with the same stem:
`00001_hr.hea` (text header: sampling rate, lead names, gain, units) and `00001_hr.dat` (binary samples).

**Where to get open-access 12-lead 500 Hz data**
| Dataset | Notes |
|---|---|
| **PTB-XL** (physionet.org/content/ptb-xl) | 21,799 × 10 s 12-lead ECGs, 500 Hz in `records500/`; open access |
| PhysioNet/CinC Challenge 2020 / 2021 | 12-lead sets from several hospitals; some at 500 Hz |

**Option 1 - copy your own files.** Copy every `.hea` + `.dat` pair into `backend/data/ecg/`. Nothing else to do.

**Option 2 - automatic download (needs internet to physionet.org):**
```bash
cd backend
python scripts/fetch_physionet_ecg.py --n 28 --clear-synthetic
```
`--clear-synthetic` removes the demo `SYN-ECG-*` files so the dashboard says **real**.

**Other formats.** `.npy` / `.npz` / `.csv` can be uploaded in the ECG Lab (enter the sampling rate). CSV: one column per lead, optional header row with lead names.

**Units.** The loader converts µV → mV automatically. NaN gaps are linearly interpolated.

---

## 2. Chest X-ray - Montgomery TB set (with lung masks)

Your CV: *"338 chest X-rays from MIMIC-CXR + Montgomery TB with clinically validated segmentation masks."*
The Montgomery County set has **138** frontal radiographs (80 normal, 58 TB) with manually drawn left/right lung masks - the only source of ground-truth masks in your mix. (338 − 138 = 200, i.e. roughly 200 MIMIC-CXR images - segmentation validation therefore covers the Montgomery part.)

1. Download `MontgomerySet.zip` from the NIH / National Library of Medicine "Tuberculosis Chest X-ray Image Data Sets" page (free, no login) and unzip.
2. Import + merge masks:
```bash
cd backend
python scripts/prepare_montgomery.py --src /path/to/MontgomerySet --clear-synthetic
```
This copies `CXR_png/*.png` → `data/xray/images/` and OR-merges `ManualMask/leftMask` + `rightMask` → `data/xray/masks/<same name>.png`.

## 3. Chest X-ray - MIMIC-CXR (credentialed)

MIMIC-CXR(-JPG) requires a PhysioNet account, **credentialing** (CITI "Data or Specimens Only Research" course) and signing the data-use agreement. Then:

- Download a small subset of the JPG version (frontal views, `PA`/`AP`).
- Copy the images into `backend/data/xray/images/` (no masks - they appear in the app with measurements only).
- **Never commit or share them.** `.gitignore` already excludes the folder.

> MIMIC-CXR-JPG images are 8-bit JPG; some other exports are 16-bit PNG or DICOM `MONOCHROME1` (air = white). 16-bit is rescaled automatically; for inverted images switch on **Invert intensities** in the X-ray Lab.

---

## 4. After importing

```bash
python scripts/evaluate_segmentation.py --all-methods --out reports/seg_eval.json   # your real numbers
```
Open **Validation** in the app to see the Dice histogram and the worst cases; click *Inspect* to open any image in the X-ray Lab and tune `morphology kernel`, `CLAHE clip` or the method.

### Typical issues on real radiographs
| Symptom | Likely cause | Fix |
|---|---|---|
| Only one lung found | lungs merged by a bright bridge / low contrast | raise CLAHE clip, lower morphology kernel, try `kmeans` |
| Mask covers whole body | air = white (inverted) | enable *Invert intensities* |
| Mask leaks into abdomen/stomach bubble | gas under diaphragm is also dark | reduce min-area, use `adaptive`, accept lower Dice or add a deep model |
| Very low Dice on TB cases | consolidations are bright → excluded from "dark" lung | known limit of intensity-only methods; fill-holes helps for small ones |

---

## Fast path: real data from Kaggle (recommended for testing)

Download with the website or the Kaggle CLI (`pip install kaggle`, put your `kaggle.json` in `~/.kaggle/`), unzip, then run the generic importer. It matches images to masks by file name, so it works on any folder layout.

| What | Kaggle dataset (search this title) | Notes |
|---|---|---|
| 12-lead ECG | **PTB-XL** (PhysioNet mirror) | use the `records500` folder = 500 Hz, matches the CV |
| Chest X-ray + lung masks | **Chest X-ray Masks and Labels** (Montgomery 138 + Shenzhen 566 images with masks) | masks are expert-drawn; Montgomery left/right masks are merged automatically |
| Montgomery only | **Tuberculosis Chest X-rays (Montgomery)** | 138 images + masks |

```bash
cd backend
python scripts/import_real_data.py ecg  --src /path/to/ptb-xl      --n 28  --clear-synthetic
python scripts/import_real_data.py xray --src /path/to/cxr-masks   --max 338 --clear-synthetic
python scripts/evaluate_ecg.py            # real numbers for your CV
python scripts/evaluate_segmentation.py   # Dice / IoU / HD95 on real masks
```

MIMIC-CXR is credentialed (PhysioNet account + CITI training) and has **no lung masks**, so it cannot be used for Dice without your own annotation. Do not upload it to Kaggle or commit it. Check each Kaggle dataset's licence before redistributing.


