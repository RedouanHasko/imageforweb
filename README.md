# Web Image Optimizer

Lightweight Flask app to convert PNG/JPEG images into optimized web-ready images (WebP, JPEG, PNG, optional AVIF).

Features
- Drag & drop multiple images
- Per-file list with name and size
- Per-file status (queued / processing / done / error)
- Upload progress + server processing percentage
- Controls for output format, quality, and max dimensions
- Asynchronous job processing with simple status & download endpoints

Requirements
- Python 3.8+
- See `requirements.txt` (Flask, Pillow). AVIF support is optional via `pillow-avif-plugin`.

Quickstart (Windows PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Optional (AVIF support):
# pip install pillow-avif-plugin
python app.py
```

Open http://127.0.0.1:8000 in your browser.

API
- `POST /start` — start an async job. Multipart form fields: `files` (one or more), `format`, `quality`, `max_width`, `max_height`. Returns `{'job_id':'...', 'total':N}`.
- `GET /status/<job_id>` — returns `{total, processed, status, error, items}`; `items` contains per-file status objects.
- `GET /download/<job_id>` — download resulting ZIP when job `status` is `done`.

Notes
- Temporary ZIPs are written to the OS temp directory and cleaned after download.
- For heavy production use: persist uploads on disk, use a background queue (Redis, RabbitMQ), and run behind a WSGI server (gunicorn, waitress).
- The frontend deduplicates files by name+size; adjust client logic if you prefer a different behavior.

Preparing to push to GitHub
1. Initialize and push
```bash
git init
git add .
git commit -m "Initial commit: web image optimizer"
git remote add origin https://github.com/<your-user>/<your-repo>.git
git branch -M main
git push -u origin main
```

2. Recommended files already included:
- `requirements.txt` — dependency list
- `.gitignore` — ignore virtualenv, caches
- `.github/workflows/ci.yml` — lightweight CI (install & smoke test)

Extras I can add
- Create an initial commit and push the repo (requires your GitHub credentials)
- Add a LICENSE (MIT recommended) and more CI steps

Security
- Add authentication, rate-limits, and file-size limits before exposing publicly.

License
- Add a LICENSE file if you plan to publish; I can add MIT for you if you want.

If you want, I can create the initial git commit and push to your GitHub (you'll need to provide a remote or give me access/config), or add LICENSE/CI refinements — tell me which.
