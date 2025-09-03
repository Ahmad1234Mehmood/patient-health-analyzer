"""Production entry point:  gunicorn wsgi:app   (Linux/macOS/Docker)  |  waitress-serve --port=5000 wsgi:app (Windows)"""
from app import create_app
from scripts.generate_synthetic_data import ensure_demo_data

app = create_app()
ensure_demo_data(app.extensions["cfg"])
