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
- See `requirements.txt` (Flask, Pillow, pdf2image). For PDF->image conversion you must also install `poppler` on your system.

Poppler install notes (Windows):

- Install via Chocolatey: `choco install poppler` (if you have Chocolatey).
- Or download a Windows poppler build and add the `bin` directory to your PATH.

After installing poppler, install Python binding:

# Web Image Optimizer

Lightweight Flask app to convert images and PDFs into web-ready images or PDFs.

Features

- Drag & drop multiple images and PDFs
- Per-file list with name and size
- Per-file status (queued / processing / done / error)
- Upload progress + server processing percentage
- Controls for output format, quality, max dimensions, and combine-PDF option
- Asynchronous job processing with status & download endpoints

Requirements

- Python 3.8+
- See `requirements.txt` for core dependencies (Flask, Pillow, pdf2image).
- Optional: `pymupdf` (PyMuPDF) provides a Poppler-free PDF renderer fallback.

PDF rendering notes

- The app prefers `pdf2image` + Poppler for PDF → image rendering (best fidelity and DPI control).
- If Poppler is not available, the app will try PyMuPDF (`pymupdf`) as a fallback if installed.

Poppler (recommended):

- Windows: install via Chocolatey `choco install poppler` or download a build and add the `bin` folder to your PATH. See https://github.com/oschwartz10612/poppler-windows/releases
- After installing Poppler, install `pdf2image` in your venv:

```powershell
pip install pdf2image
```

PyMuPDF fallback (no Poppler required):

```powershell
pip install pymupdf
```

Quickstart (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Optional fallbacks:
# pip install pdf2image   # requires Poppler
# pip install pymupdf     # PyMuPDF fallback renderer
python app.py
```

Open http://127.0.0.1:8000 in your browser.

Usage

- In the UI choose `Format` (WebP, JPEG, PNG, AVIF, PDF).
- For `Format = PDF` you can enable `Combine all images into a single PDF` to produce a single multi-page PDF.
- For PDF → image conversions, higher `Quality` increases the rendering DPI and resulting file size.

API

- `POST /start` — start an async job. Multipart form fields: `files` (one or more), `format`, `quality`, `max_width`, `max_height`, `combine_pdf` (0/1). Returns `{'job_id':'...', 'total':N}`.
- `GET /status/<job_id>` — returns `{total, processed, status, error, items}`; `items` contains per-file status objects.
- `GET /download/<job_id>` — download resulting ZIP when job `status` is `done`.

Notes

- Temporary ZIPs are written to the OS temp directory and cleaned after download.
- For production: persist uploads on disk, use a background queue and run behind a WSGI server (gunicorn, waitress).

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

2. Files included

- `requirements.txt` — dependency list
- `.gitignore` — ignore virtualenv, caches
- `.github/workflows/ci.yml` — lightweight CI (install & smoke test)

License

- Add a `LICENSE` file if you plan to publish; I can add the MIT license for you if you want.

If you'd like I can also:

- Add an explicit `dpi` control to the UI
- Add a combined-PDF preview
- Create the initial commit and push to GitHub (requires remote/credentials)
