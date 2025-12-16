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
 # Web Image Optimizer

Lightweight Flask app to convert images and PDFs into optimized web-ready images, PDFs, or editable DOCX documents.

## Features

- Drag & drop multiple images and PDFs
- Per-file list with name and size
- Per-file status (queued / processing / done / error)
- Upload progress + server processing percentage
- Controls for output format, quality, max dimensions, combine-PDF option
- DOCX export (digital PDFs via `pdf2docx` or layout-preserving conversion with LibreOffice)
- OCR fallback for scanned PDFs / images (Tesseract) producing editable `.docx`
- Asynchronous job processing with `/start`, `/status/<job_id>`, `/download/<job_id>` endpoints

## Requirements

- Python 3.8+
- See `requirements.txt` for Python dependencies. New optional items for DOCX/OCR:
	- `pdf2docx` — convert digital (text-based) PDFs to `.docx`
	- `python-docx` — build `.docx` files when using OCR or PyMuPDF text extraction
	- `pytesseract` — OCR engine binding (requires Tesseract binary installed)
- Optional: `pymupdf` (PyMuPDF) provides PDF access and a poppler-free rendering/text extraction fallback.
- Optional (best visual fidelity for PDF→DOCX): LibreOffice (`soffice`) installed locally when using "Preserve layout".

### Installing system tools

- **Poppler** (recommended for `pdf2image` rendering):
	- Windows: `choco install poppler` or download a Windows build and add its `bin` folder to `PATH`.
	- See: https://github.com/oschwartz10612/poppler-windows/releases

- **Tesseract OCR** (for `pytesseract`):
	- Windows: install from https://github.com/UB-Mannheim/tesseract/wiki and add `tesseract.exe` to PATH.

- **LibreOffice** (optional, for best layout-preserving PDF→DOCX):
	- Install LibreOffice and ensure `soffice`/`soffice.exe` is on `PATH`.

### Python dependencies

Install Python deps in your venv:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If you plan to use Poppler/PyMuPDF/LibreOffice/Tesseract, install those system packages as noted above.

## Quickstart

```powershell
# activate venv (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:8000 in your browser.

## Usage notes

- Format options: `webp`, `jpeg`, `png`, `avif`, `pdf`, `docx`.
- DOCX behavior:
	- If `Preserve layout (LibreOffice)` is enabled and LibreOffice (`soffice`) is installed, the server will run `soffice --headless --convert-to docx` to produce a DOCX that closely matches the PDF layout.
	- Otherwise, for digital PDFs the app will try `pdf2docx` (good structure preservation).
	- If the PDF is a scanned image or the other tools are unavailable, enable `OCR` to run Tesseract on page images and produce editable text in a `.docx` (layout may differ).

- OCR: enable `OCR` for scanned PDFs / image inputs. Requires `pytesseract` and the Tesseract binary.
- Combine PDF: when `Format=PDF` you can enable `Combine into a single PDF` to produce one multi-page PDF from uploaded images.

## API

- `POST /start` — start an async job. Multipart form fields:
	- `files`: uploaded files (one or more)
	- `format`: `webp|jpeg|png|avif|pdf|docx`
	- `quality`: numeric (10-100)
	- `max_width`, `max_height`: optional
	- `combine_pdf`: `0` or `1` (for PDF output)
	- `ocr`: `0` or `1` (use OCR for scanned inputs)
	- `preserve_layout`: `0` or `1` (use LibreOffice `soffice` for PDF→DOCX when available)
	Returns `{'job_id':'...', 'total':N}` on success.
- `GET /status/<job_id>` — returns `{total, processed, status, error, items}`; `items` contains per-file status objects.
- `GET /download/<job_id>` — download resulting ZIP when job `status` is `done`.

## Notes

- Temporary ZIPs are written to the OS temp directory and removed after download.
- For production: persist uploads to disk, use a task queue (Redis/RQ, Celery), and run behind a WSGI server (gunicorn, waitress).

## Troubleshooting

- If DOCX output looks wrong:
	- Try enabling `Preserve layout` and make sure LibreOffice (`soffice`) is installed on the machine.
	- For scanned PDFs, enable `OCR` and/or run `ocrmypdf` before conversion for best searchable text embedding.
- If PDF→image renders poorly, install Poppler or `pymupdf`.

## Preparing to push to GitHub

```bash
git init
git add .
git commit -m "Add web image optimizer with DOCX/OCR support"
git remote add origin https://github.com/<your-user>/<your-repo>.git
git branch -M main
git push -u origin main
```

If you want, I can also help add an explicit `dpi` control, wire `ocrmypdf` into the workflow, or create a small test harness for DOCX conversions.
