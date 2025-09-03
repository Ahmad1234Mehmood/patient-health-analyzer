"""Entry point.  `python run.py`  ->  http://localhost:5000"""
from __future__ import annotations

import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    cfg = app.extensions["cfg"]
    # First-run convenience: if no data exists, generate the synthetic demo dataset.
    from scripts.generate_synthetic_data import ensure_demo_data

    ensure_demo_data(cfg)
    debug = cfg.environment == "development"
    if debug:
        # Never expose the Werkzeug debugger beyond this computer.
        app.run(host="127.0.0.1", port=cfg.port, debug=True)
    elif os.name != "nt":
        app.run(host="0.0.0.0", port=cfg.port, debug=False)
    else:
        from waitress import serve

        serve(app, host="0.0.0.0", port=cfg.port)
