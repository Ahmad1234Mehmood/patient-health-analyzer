"""ECG record loading.

Supported inputs
----------------
* WFDB (PhysioNet) pairs  : `name.hea` + `name.dat`   (the native PhysioNet format)
* NumPy                   : `.npy` / `.npz` arrays shaped (samples, leads) or (leads, samples)
* CSV                     : one column per lead (optional header row with lead names)

All records are converted to millivolts, shape (n_samples, n_leads), plus a sampling rate `fs`.
"""
from __future__ import annotations

import csv
import io
import json
import re
import secrets
import tempfile
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from app.utils.errors import ApiError

LEADS_12 = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]
_ALIASES = {n.lower(): n for n in LEADS_12}
_ALIASES.update({"avr": "aVR", "avl": "aVL", "avf": "aVF", "lead1": "I", "lead2": "II"})
_SAFE_ID = re.compile(r"^[A-Za-z0-9_.\-]+$")


def normalize_lead_name(name: str) -> str:
    key = name.strip().replace(" ", "").lower()
    return _ALIASES.get(key, name.strip())


@dataclass
class ECGRecord:
    id: str
    signal: np.ndarray            # (n_samples, n_leads) in mV
    fs: float
    lead_names: list[str]
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def n_samples(self) -> int:
        return int(self.signal.shape[0])

    @property
    def n_leads(self) -> int:
        return int(self.signal.shape[1])

    @property
    def duration_s(self) -> float:
        return self.n_samples / self.fs

    def lead_index(self, lead: str | int) -> int:
        if isinstance(lead, int):
            idx = lead
        else:
            names = [n.lower() for n in self.lead_names]
            wanted = normalize_lead_name(str(lead)).lower()
            if wanted not in names:
                raise ApiError(f"Lead '{lead}' not in record. Available: {', '.join(self.lead_names)}", 400)
            idx = names.index(wanted)
        if not 0 <= idx < self.n_leads:
            raise ApiError("Lead index out of range", 400)
        return idx

    def summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "fs": self.fs,
            "n_leads": self.n_leads,
            "lead_names": self.lead_names,
            "n_samples": self.n_samples,
            "duration_s": round(self.duration_s, 3),
            **{k: v for k, v in self.meta.items() if k != "r_times"},
        }


def _fill_nans(sig: np.ndarray) -> np.ndarray:
    """Linear interpolation over NaN gaps (PhysioNet files can contain them)."""
    if not np.isnan(sig).any():
        return sig
    out = sig.copy()
    x = np.arange(sig.shape[0])
    for j in range(sig.shape[1]):
        bad = np.isnan(out[:, j])
        if bad.all():
            out[:, j] = 0.0
        elif bad.any():
            out[bad, j] = np.interp(x[bad], x[~bad], out[~bad, j])
    return out


def _read_wfdb(path_no_ext: Path, record_id: str) -> ECGRecord:
    import wfdb  # imported lazily so the rest of the API works even without wfdb

    try:
        rec = wfdb.rdrecord(str(path_no_ext))
    except Exception as exc:  # wfdb raises many different exception types
        raise ApiError(f"Could not read WFDB record '{record_id}': {exc}", 422, "bad_record") from exc
    if rec.p_signal is None:
        raise ApiError("WFDB record has no physical signal", 422, "bad_record")
    sig = _fill_nans(np.asarray(rec.p_signal, dtype=np.float64))
    units = [str(u).lower() for u in (rec.units or [])]
    for j, u in enumerate(units[: sig.shape[1]]):
        if u in ("uv", "µv", "μv"):
            sig[:, j] /= 1000.0  # uV -> mV
        elif u == "v":
            sig[:, j] *= 1000.0
    names = [normalize_lead_name(n) for n in (rec.sig_name or [])]
    if len(names) != sig.shape[1]:
        names = LEADS_12[: sig.shape[1]] if sig.shape[1] == 12 else [f"Lead{i + 1}" for i in range(sig.shape[1])]
    return ECGRecord(record_id, sig, float(rec.fs), names, {"format": "wfdb", "comments": list(rec.comments or [])})


def _orient(arr: np.ndarray) -> np.ndarray:
    if arr.ndim == 1:
        arr = arr[:, None]
    if arr.ndim != 2:
        raise ApiError("ECG array must be 1-D or 2-D", 422, "bad_record")
    if arr.shape[0] <= 16 and arr.shape[1] > 16:  # (leads, samples) -> (samples, leads)
        arr = arr.T
    return arr


def _parse_csv(data: bytes) -> tuple[np.ndarray, list[str] | None]:
    text = data.decode("utf-8", errors="replace")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t ")
        delim = dialect.delimiter
    except csv.Error:
        delim = ","
    rows = [r for r in csv.reader(io.StringIO(text), delimiter=delim) if r]
    header = None
    try:
        [float(x) for x in rows[0]]
    except ValueError:
        header, rows = [c.strip() for c in rows[0]], rows[1:]
    try:
        arr = np.array([[float(x) for x in r] for r in rows], dtype=np.float64)
    except ValueError as exc:
        raise ApiError("CSV contains non-numeric values", 422, "bad_record") from exc
    return arr, header


def _from_array(arr: np.ndarray, record_id: str, fs: float, names: list[str] | None, fmt: str) -> ECGRecord:
    arr = _fill_nans(_orient(np.asarray(arr, dtype=np.float64)))
    if arr.shape[0] < int(2 * fs):
        raise ApiError("Record shorter than 2 seconds - cannot analyse", 422, "bad_record")
    n = arr.shape[1]
    if not names or len(names) != n:
        names = LEADS_12 if n == 12 else [f"Lead{i + 1}" for i in range(n)]
    return ECGRecord(record_id, arr, float(fs), [normalize_lead_name(x) for x in names], {"format": fmt})


class ECGRepository:
    """Disk-backed list of ECG records + small in-memory cache for uploaded files."""

    def __init__(self, ecg_dir: Path, max_uploads: int = 8):
        self.dir = Path(ecg_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._uploads: "OrderedDict[str, ECGRecord]" = OrderedDict()
        self._max_uploads = max_uploads

    # ----------------------------------------------------------------- listing
    def _manifest(self) -> dict[str, Any]:
        p = self.dir / "manifest.json"
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {}
        return {}

    def list_records(self) -> list[dict[str, Any]]:
        import wfdb

        manifest = self._manifest()
        out: list[dict[str, Any]] = []
        for hea in sorted(self.dir.glob("*.hea")):
            rid = hea.stem
            try:
                h = wfdb.rdheader(str(hea.with_suffix("")))
            except Exception:
                continue
            info = {
                "id": rid,
                "fs": float(h.fs),
                "n_leads": int(h.n_sig),
                "n_samples": int(h.sig_len),
                "duration_s": round(h.sig_len / h.fs, 2),
                "lead_names": [normalize_lead_name(n) for n in h.sig_name],
                "format": "wfdb",
            }
            info.update({k: v for k, v in manifest.get(rid, {}).items() if k != "r_times"})
            out.append(info)
        for npz in sorted(self.dir.glob("*.npz")):
            out.append({"id": npz.stem, "format": "npz", **{k: v for k, v in manifest.get(npz.stem, {}).items() if k != "r_times"}})
        return out

    # ----------------------------------------------------------------- reading
    def get(self, record_id: str) -> ECGRecord:
        if record_id in self._uploads:
            self._uploads.move_to_end(record_id)
            return self._uploads[record_id]
        if not _SAFE_ID.match(record_id or ""):
            raise ApiError("Invalid record id", 400)
        base = self.dir / record_id
        manifest_meta = self._manifest().get(record_id, {})
        if base.with_suffix(".hea").exists():
            rec = _read_wfdb(base, record_id)
        elif base.with_suffix(".npz").exists():
            z = np.load(base.with_suffix(".npz"))
            rec = _from_array(z["signal"], record_id, float(z["fs"]), list(z["leads"]) if "leads" in z else None, "npz")
        else:
            raise ApiError(f"ECG record '{record_id}' not found", 404, "not_found")
        rec.meta.update(manifest_meta)
        return rec

    # ----------------------------------------------------------------- uploads
    def add_upload(self, files: dict[str, bytes], fs: float | None) -> ECGRecord:
        """files: {filename: bytes}. Accepts a .hea+.dat pair, or one .csv/.npy/.npz file."""
        names = {Path(n).name: b for n, b in files.items()}
        lower = {n.lower(): n for n in names}
        rid = f"upload-{secrets.token_hex(3)}"
        heas = [n for n in lower if n.endswith(".hea")]
        if heas:
            with tempfile.TemporaryDirectory() as tmp:
                for n, b in names.items():
                    if _SAFE_ID.match(n):
                        (Path(tmp) / n).write_bytes(b)
                stem = Path(lower[heas[0]]).stem
                rec = _read_wfdb(Path(tmp) / stem, rid)
                rec.meta["original_name"] = stem
        else:
            fname = next(iter(names), "")
            ext = Path(fname).suffix.lower()
            data = names[fname]
            fs_val = float(fs or 500.0)
            if ext == ".csv" or ext == ".txt":
                arr, header = _parse_csv(data)
                rec = _from_array(arr, rid, fs_val, header, "csv")
            elif ext == ".npy":
                rec = _from_array(np.load(io.BytesIO(data), allow_pickle=False), rid, fs_val, None, "npy")
            elif ext == ".npz":
                z = np.load(io.BytesIO(data), allow_pickle=False)
                key = "signal" if "signal" in z else z.files[0]
                rec = _from_array(z[key], rid, float(z["fs"]) if "fs" in z else fs_val, None, "npz")
            else:
                raise ApiError("Unsupported file. Use .hea+.dat (WFDB), .csv, .npy or .npz", 415, "unsupported")
            rec.meta["original_name"] = fname
        rec.meta["source"] = "upload"
        self._uploads[rid] = rec
        while len(self._uploads) > self._max_uploads:
            self._uploads.popitem(last=False)
        return rec
