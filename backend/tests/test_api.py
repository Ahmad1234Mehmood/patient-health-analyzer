from __future__ import annotations

import io


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json["status"] == "healthy"


def test_datasets_summary(client):
    j = client.get("/api/v1/datasets/summary").json
    assert j["ecg"]["count"] == 8 and j["ecg"]["sampling_rates_hz"] == [500.0] and j["ecg"]["mode"] == "synthetic"
    assert j["xray"]["count"] == 8 and j["xray"]["with_masks"] == 8


def test_ecg_list_and_analyze(client):
    recs = client.get("/api/v1/ecg/records").json["records"]
    assert len(recs) == 8 and recs[0]["n_leads"] == 12
    rid = recs[0]["id"]
    r = client.post("/api/v1/ecg/analyze", json={"record_id": rid, "lead": "II"})
    assert r.status_code == 200
    j = r.json
    for key in ("signal", "r_peaks", "hrv", "spectrum", "autocorr", "quality", "template", "leads_summary", "findings"):
        assert key in j
    assert len(j["leads_summary"]) == 12 and len(j["signal"]["t_s"]) <= 3000
    truth = next(x for x in recs if x["id"] == rid)["hr_true"]
    assert abs(j["hrv"]["hr_bpm"] - truth) < 3


def test_ecg_filter_params_validated(client):
    rid = client.get("/api/v1/ecg/records").json["records"][0]["id"]
    r = client.post("/api/v1/ecg/analyze", json={"record_id": rid, "low_hz": 40, "high_hz": 0.5})
    assert r.status_code == 400 and r.json["error"] == "bad_request"
    r = client.post("/api/v1/ecg/analyze", json={"record_id": rid, "lead": "Z9"})
    assert r.status_code == 400
    r = client.post("/api/v1/ecg/analyze", json={})
    assert r.status_code == 400


def test_ecg_not_found_and_path_traversal(client):
    assert client.post("/api/v1/ecg/analyze", json={"record_id": "nope"}).status_code == 404
    assert client.post("/api/v1/ecg/analyze", json={"record_id": "../../etc/passwd"}).status_code in (400, 404)


def test_ecg_csv_upload_roundtrip(client):
    import numpy as np
    from app.services.ecg.synthetic import synth_ecg

    sig, _ = synth_ecg(10, 250, 80, seed=4)
    buf = io.StringIO()
    buf.write("I,II,III,aVR,aVL,aVF,V1,V2,V3,V4,V5,V6\n")
    np.savetxt(buf, sig, delimiter=",", fmt="%.5f")
    data = {"files": (io.BytesIO(buf.getvalue().encode()), "mine.csv"), "fs": "250"}
    up = client.post("/api/v1/ecg/upload", data=data, content_type="multipart/form-data")
    assert up.status_code == 201
    rid = up.json["record"]["id"]
    assert up.json["record"]["fs"] == 250
    j = client.post("/api/v1/ecg/analyze", json={"record_id": rid, "lead": "V5"}).json
    assert abs(j["hrv"]["hr_bpm"] - 80) < 4


def test_filter_response(client):
    j = client.get("/api/v1/ecg/filter-response?low_hz=0.5&high_hz=40&order=4&fs=500").json
    assert len(j["freqs_hz"]) == len(j["zero_phase_db"]) > 100


def test_xray_list_analyze_evaluate(client):
    imgs = client.get("/api/v1/xray/images").json["images"]
    assert len(imgs) == 8 and imgs[0]["has_mask"]
    r = client.post("/api/v1/xray/analyze", json={"image_id": imgs[0]["id"], "method": "otsu"})
    assert r.status_code == 200 and r.json["validation"]["dice"] > 0.85
    bad = client.post("/api/v1/xray/analyze", json={"image_id": imgs[0]["id"], "method": "magic"})
    assert bad.status_code == 400
    ev = client.get("/api/v1/xray/evaluate?method=kmeans").json
    assert ev["n"] == 8 and ev["summary"]["dice"]["mean"] > 0.9


def test_xray_upload_and_history(client):
    import cv2, numpy as np
    from app.services.xray.synthetic import make_phantom

    img, _ = make_phantom(np.random.default_rng(1), 400)
    ok, buf = cv2.imencode(".png", img)
    up = client.post("/api/v1/xray/upload", data={"file": (io.BytesIO(buf.tobytes()), "mine.png")}, content_type="multipart/form-data")
    iid = up.json["image"]["id"]
    r = client.post("/api/v1/xray/analyze", json={"image_id": iid, "save": True})
    assert r.status_code == 200 and "validation" not in r.json and r.json["saved_id"] >= 1
    hist = client.get("/api/v1/history").json["items"]
    assert hist[0]["kind"] == "xray"
    assert client.delete(f"/api/v1/history/{hist[0]['id']}").status_code == 200
    assert client.get("/api/v1/history").json["items"] == []


def test_bad_upload_rejected(client):
    r = client.post("/api/v1/xray/upload", data={"file": (io.BytesIO(b"not an image"), "x.png")}, content_type="multipart/form-data")
    assert r.status_code == 415
    r = client.post("/api/v1/ecg/upload", data={"files": (io.BytesIO(b"abc"), "x.exe")}, content_type="multipart/form-data")
    assert r.status_code == 415
