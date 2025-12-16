# app.py
# Professional lightweight web app to convert PNG/JPEG images to optimized web-ready images
# FIXED VERSION: Uses Flask instead of FastAPI to avoid SSL module dependency issues
# Stack: Flask + Pillow + clean modern UI (Tailwind CDN)

from flask import Flask, request, send_file, Response, jsonify
from PIL import Image
import io
import zipfile
import threading
import uuid
import tempfile
import os
import time

# In-memory job store. For production consider a persistent queue/storage.
jobs = {}
jobs_lock = threading.Lock()

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return """
<!DOCTYPE html>
<html lang='en'>
<head>
  <meta charset='UTF-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1.0'>
  <title>Image Optimizer</title>
  <script src='https://cdn.tailwindcss.com'></script>
  <style>
    .drag-active { border: 2px dashed #6366f1 !important; background: #3730a3 !important; }
  </style>
</head>
<body class='bg-zinc-900 text-white min-h-screen flex items-center justify-center'>
  <div class='w-full max-w-xl bg-zinc-800 rounded-2xl p-8 shadow-xl'>
    <h1 class='text-2xl font-bold mb-2'>Web Image Optimizer</h1>
    <p class='text-zinc-400 mb-6'>Convert PNG & JPEG images into lightweight, web-optimized images with best quality.</p>

    <!-- Drag and Drop Area -->
    <form id='uploadForm' action='/optimize' method='post' enctype='multipart/form-data'>
      <div id='dropArea' class='relative w-full mb-4 flex flex-col items-center justify-center border-2 border-dashed border-zinc-600 rounded-lg p-6 transition'>
        <svg class='w-10 h-10 mb-2 text-indigo-400' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' d='M7 16V4a1 1 0 0 1 1-1h8a1 1 0 0 1 1 1v12m-5 4v-4m0 0l-2 2m2-2l2 2'></path></svg>
        <span class='text-zinc-400'>Drag & drop images here or click to select</span>
        <input id='fileInput' type='file' name='files' multiple accept='image/png,image/jpeg' class='absolute inset-0 opacity-0 cursor-pointer' />
      </div>

      <div class='flex justify-between mb-4 text-sm'>
        <span id='imageCount' class='text-zinc-400'>No images selected</span>
        <span id='processedCount' class='text-zinc-400'></span>
      </div>
      <div id='fileList' class='mb-4 text-sm'></div>

        <div class='grid grid-cols-2 gap-2 mb-4'>
          <label class='text-zinc-300 text-xs'>Format
            <select name='format' class='w-full mt-1 bg-zinc-700 rounded-lg p-2'>
              <option value='webp'>WebP (Recommended)</option>
              <option value='jpeg'>JPEG</option>
              <option value='png'>PNG</option>
              <option value='avif'>AVIF (optional)</option>
            </select>
          </label>

          <label class='text-zinc-300 text-xs'>Quality
            <div class='mt-1 flex items-center space-x-2'>
              <input id='qualityRange' name='quality' type='range' min='10' max='100' value='85' class='w-full' />
              <div id='qualityVal' class='w-14 text-right text-zinc-300'>85</div>
            </div>
          </label>

          <label class='text-zinc-300 text-xs'>Max Width (px)
            <input name='max_width' type='number' min='0' placeholder='1920' class='w-full mt-1 bg-zinc-700 rounded-lg p-2' />
          </label>

          <label class='text-zinc-300 text-xs'>Max Height (px)
            <input name='max_height' type='number' min='0' placeholder='1080' class='w-full mt-1 bg-zinc-700 rounded-lg p-2' />
          </label>
        </div>

        <button id='submitBtn' type='submit' class='w-full bg-indigo-600 hover:bg-indigo-700 transition rounded-lg py-3 font-semibold'>
          Start
        </button>
    </form>

    <div id='progressArea' class='mt-4 hidden'>
      <div class='w-full bg-zinc-700 rounded-lg h-4 mb-2'>
        <div id='progressBar' class='bg-indigo-500 h-4 rounded-lg transition-all' style='width:0%'></div>
      </div>
      <div class='flex justify-between text-xs'>
        <span id='progressText'>0%</span>
        <span id='statusMsg'></span>
      </div>
    </div>
  </div>
  <script>
    // Drag and drop logic
    const dropArea = document.getElementById('dropArea');
    const fileInput = document.getElementById('fileInput');
    const uploadForm = document.getElementById('uploadForm');
    const imageCount = document.getElementById('imageCount');
    const processedCount = document.getElementById('processedCount');
    const progressArea = document.getElementById('progressArea');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const statusMsg = document.getElementById('statusMsg');
    let files = [];

    function updateImageCount() {
      if (files.length === 0) {
        imageCount.textContent = 'No images selected';
      } else {
        imageCount.textContent = files.length + ' image' + (files.length > 1 ? 's' : '') + ' selected';
      }
    }

    function renderFileList(serverItems) {
      // serverItems is optional array from /status, same order as files
      const list = document.getElementById('fileList');
      if (!files || files.length === 0) {
        list.innerHTML = '';
        return;
      }
      let html = "<div class='space-y-2'>";
      files.forEach((f, i) => {
        const sizeKB = Math.round(f.size / 1024);
        const ext = (f.name || f.type).split('/').pop() || (f.name && f.name.split('.').pop()) || '';
        let status = 'queued';
        let out = '';
        if (serverItems && serverItems[i]) {
          status = serverItems[i].status || status;
          out = serverItems[i].out_name ? (' → ' + serverItems[i].out_name) : '';
        }
        const color = status === 'done' ? 'text-green-400' : status === 'processing' ? 'text-indigo-300' : status === 'error' ? 'text-red-400' : 'text-zinc-400';
        html += `<div class='flex justify-between items-center bg-zinc-700 p-2 rounded-lg'>`;
        html += `<div class='truncate'><strong>${f.name}</strong> <span class='text-zinc-400'>(${sizeKB} KB)</span>${out}</div>`;
        html += `<div class='ml-4 ${color}'>${status}</div>`;
        html += `</div>`;
      });
      html += "</div>";
      list.innerHTML = html;
    }

    // Quality slider sync
    const qualityRange = document.getElementById('qualityRange');
    const qualityVal = document.getElementById('qualityVal');
    if (qualityRange && qualityVal) {
      qualityRange.addEventListener('input', (e) => { qualityVal.textContent = e.target.value; });
    }

    dropArea.addEventListener('click', (e) => {
      // Prevent double-opening: if the real file input was the target, don't re-trigger click
      if (e.target === fileInput) return;
      fileInput.click();
    });
    dropArea.addEventListener('dragover', e => {
      e.preventDefault();
      dropArea.classList.add('drag-active');
    });
    dropArea.addEventListener('dragleave', e => {
      e.preventDefault();
      dropArea.classList.remove('drag-active');
    });
    dropArea.addEventListener('drop', e => {
      e.preventDefault();
      dropArea.classList.remove('drag-active');
      const dropped = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/'));
      // append new files, dedupe by name+size
      dropped.forEach(df => { if (!files.some(f => f.name === df.name && f.size === df.size)) files.push(df); });
      // sync hidden input to reflect all files
      const dt = new DataTransfer(); files.forEach(f => dt.items.add(f)); fileInput.files = dt.files;
      updateImageCount();
      renderFileList();
    });
    fileInput.addEventListener('change', e => {
      const newly = Array.from(fileInput.files).filter(f => f.type.startsWith('image/'));
      newly.forEach(nf => { if (!files.some(f => f.name === nf.name && f.size === nf.size)) files.push(nf); });
      // rebuild fileInput.files to include all files
      const dt2 = new DataTransfer(); files.forEach(f => dt2.items.add(f)); fileInput.files = dt2.files;
      updateImageCount();
      renderFileList();
    });

    // Progress and status logic
    uploadForm.addEventListener('submit', function(e) {
      e.preventDefault();
      statusMsg.textContent = '';
      statusMsg.className = '';
      if (files.length === 0) {
        statusMsg.textContent = 'Please select at least one image.';
        statusMsg.className = 'text-red-400';
        return;
      }
      progressArea.classList.remove('hidden');
      progressBar.style.width = '0%';
      progressText.textContent = '0%';
      processedCount.textContent = '';

      // Build form data manually to avoid duplicating file inputs
      const formData = new FormData();
      // append controls
      const format = uploadForm.querySelector('select[name="format"]').value;
      const maxw = uploadForm.querySelector('input[name="max_width"]').value || '';
      const maxh = uploadForm.querySelector('input[name="max_height"]').value || '';
      const qualityControl = document.getElementById('qualityRange');
      const qualityValToSend = qualityControl ? qualityControl.value : (uploadForm.querySelector('input[name="quality"]') ? uploadForm.querySelector('input[name="quality"]').value : '85');
      formData.append('format', format);
      formData.append('quality', qualityValToSend);
      formData.append('max_width', maxw);
      formData.append('max_height', maxh);
      // append files from our managed `files` array
      files.forEach(f => formData.append('files', f));

      // Use XHR so we can track upload progress for UX
      const xhr = new XMLHttpRequest();
      xhr.open('POST', '/start', true);
      xhr.responseType = 'json';

      xhr.upload.onprogress = function(e) {
        if (e.lengthComputable) {
          const percent = Math.round((e.loaded / e.total) * 100 * 0.4); // upload is ~40% of the visual progress
          progressBar.style.width = percent + '%';
          progressText.textContent = percent + '%';
        }
      };

      xhr.onload = function() {
        if (xhr.status === 200 && xhr.response && xhr.response.job_id) {
          const jobId = xhr.response.job_id;
          const total = xhr.response.total || files.length;
          imageCount.textContent = total + ' image' + (total > 1 ? 's' : '') + ' queued';

          // Poll status
          const poll = setInterval(async () => {
            try {
              const res = await fetch(`/status/${jobId}`);
              const data = await res.json();
              if (data.error) {
                clearInterval(poll);
                statusMsg.textContent = 'Error: ' + data.error;
                statusMsg.className = 'text-red-400';
                return;
              }
              // update per-file statuses if available
              if (data.items) {
                renderFileList(data.items);
              }
              const proc = data.processed || 0;
              const tot = data.total || total;
              const serverPercent = Math.round((proc / (tot || 1)) * 100 * 0.6); // remaining 60%
              const uploadPercent = parseInt(progressText.textContent) || 0;
              const combined = Math.min(100, uploadPercent + serverPercent);
              progressBar.style.width = combined + '%';
              progressText.textContent = combined + '%';
              processedCount.textContent = proc + ' / ' + tot + ' processed';

              if (data.status === 'done') {
                clearInterval(poll);
                progressBar.style.width = '100%';
                progressText.textContent = '100%';
                statusMsg.textContent = 'Done!';
                statusMsg.className = 'text-green-400';
                // Download
                fetch(`/download/${jobId}`).then(r => r.blob()).then(blob => {
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = 'optimized_images.zip';
                  document.body.appendChild(a);
                  a.click();
                  setTimeout(() => {
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                  }, 100);
                }).catch(err => {
                  statusMsg.textContent = 'Download error';
                  statusMsg.className = 'text-red-400';
                });
              } else if (data.status === 'error') {
                clearInterval(poll);
                statusMsg.textContent = 'Error: ' + data.error;
                statusMsg.className = 'text-red-400';
              }
            } catch (err) {
              clearInterval(poll);
              statusMsg.textContent = 'Status error';
              statusMsg.className = 'text-red-400';
            }
          }, 600);

        } else {
          statusMsg.textContent = 'Failed to start job.';
          statusMsg.className = 'text-red-400';
        }
      };

      xhr.onerror = function() {
        statusMsg.textContent = 'Network error.';
        statusMsg.className = 'text-red-400';
      };

      xhr.send(formData);
    });
  </script>
</body>
</html>
"""

@app.route("/optimize", methods=["POST"])
def optimize_images():
    files = request.files.getlist("files")
    output_format = request.form.get("format", "webp")

    if not files:
        return Response("No files uploaded", status=400)

    zip_buffer = io.BytesIO()
    processed = 0
    try:
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in files:
                try:
                    img = Image.open(file.stream).convert('RGB')
                    output = io.BytesIO()
                    if output_format == 'webp':
                        img.save(output, format='WEBP', quality=85, method=6)
                        ext = 'webp'
                    else:
                        img.save(output, format='JPEG', quality=85, optimize=True, progressive=True)
                        ext = 'jpg'
                    filename = file.filename.rsplit('.', 1)[0]
                    zipf.writestr(f"{filename}.{ext}", output.getvalue())
                    processed += 1
                except Exception as e:
                    # If one image fails, skip and continue
                    continue
        zip_buffer.seek(0)
        if processed == 0:
            return Response("All images failed to process.", status=500)
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name='optimized_images.zip'
        )
    except Exception as e:
        return Response(f"Error: {str(e)}", status=500)

# =============================
# BASIC TEST CASES (MANUAL)
# =============================
# 1. Upload multiple PNG files → receive ZIP with .webp images
# 2. Upload multiple JPEG files → receive ZIP with optimized .jpg images
# 3. Upload mixed PNG/JPEG → all converted correctly
# 4. Upload nothing → returns HTTP 400

# Run with:
# pip install flask pillow


def _process_job(job_id, file_blobs, output_format, quality, max_w, max_h):
  """Background worker to process images for a job and write a ZIP to disk.
  Updates the shared `jobs` dict with progress.
  """
  try:
    zip_buffer = io.BytesIO()
    processed = 0
    total = len(file_blobs)
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
      for idx, (name, blob) in enumerate(file_blobs):
        # mark processing
        with jobs_lock:
          if job_id in jobs and 'items' in jobs[job_id] and idx < len(jobs[job_id]['items']):
            jobs[job_id]['items'][idx]['status'] = 'processing'
        try:
          img = Image.open(io.BytesIO(blob)).convert('RGB')
          # Resize if needed while preserving aspect ratio
          if max_w or max_h:
            mw = int(max_w) if max_w else None
            mh = int(max_h) if max_h else None
            if mw or mh:
              target = (mw or img.width, mh or img.height)
              img.thumbnail(target, Image.LANCZOS)
          out = io.BytesIO()
          if output_format == 'webp':
            img.save(out, format='WEBP', quality=quality, method=6)
            ext = 'webp'
          elif output_format == 'png':
            img.save(out, format='PNG', optimize=True)
            ext = 'png'
          elif output_format == 'avif':
            try:
              img.save(out, format='AVIF', quality=quality)
              ext = 'avif'
            except Exception:
              img.save(out, format='WEBP', quality=quality, method=6)
              ext = 'webp'
          else:
            img.save(out, format='JPEG', quality=quality, optimize=True, progressive=True)
            ext = 'jpg'

          filename = os.path.splitext(name)[0]
          zipf.writestr(f"{filename}.{ext}", out.getvalue())
          processed += 1
          # update per-item status
          with jobs_lock:
            if job_id in jobs and 'items' in jobs[job_id] and idx < len(jobs[job_id]['items']):
              jobs[job_id]['items'][idx]['status'] = 'done'
              jobs[job_id]['items'][idx]['out_name'] = f"{filename}.{ext}"
            jobs[job_id]['processed'] = processed
        except Exception as e:
          with jobs_lock:
            if job_id in jobs and 'items' in jobs[job_id] and idx < len(jobs[job_id]['items']):
              jobs[job_id]['items'][idx]['status'] = 'error'
              jobs[job_id]['items'][idx]['error'] = str(e)
            jobs[job_id]['processed'] = processed
          continue

    # Persist zip to temp file
    zip_buffer.seek(0)
    tmp_path = os.path.join(tempfile.gettempdir(), f"{job_id}.zip")
    with open(tmp_path, 'wb') as f:
      f.write(zip_buffer.getvalue())

    with jobs_lock:
      jobs[job_id]['status'] = 'done'
      jobs[job_id]['path'] = tmp_path
  except Exception as e:
    with jobs_lock:
      jobs[job_id]['status'] = 'error'
      jobs[job_id]['error'] = str(e)


@app.route('/start', methods=['POST'])
def start_job():
  """Start an async processing job. Returns a JSON job id and total files.
  Client should poll `/status/<job_id>` and then download from `/download/<job_id>`.
  """
  files = request.files.getlist('files')
  if not files:
    return jsonify({'error': 'No files uploaded'}), 400

  output_format = request.form.get('format', 'webp')
  try:
    quality = int(request.form.get('quality', 85))
  except Exception:
    quality = 85
  max_w = request.form.get('max_width') or None
  max_h = request.form.get('max_height') or None

  # Read all files into memory (safe for small uploads). For large uploads store on disk.
  file_blobs = []
  items = []
  for f in files:
    try:
      blob = f.read()
      file_blobs.append((f.filename or 'image', blob))
      items.append({'name': f.filename or 'image', 'size': len(blob), 'status': 'queued'})
    except Exception:
      continue

  job_id = uuid.uuid4().hex
  with jobs_lock:
    jobs[job_id] = {'total': len(file_blobs), 'processed': 0, 'status': 'processing', 'error': None, 'path': None, 'items': items}

  # Start background worker
  t = threading.Thread(target=_process_job, args=(job_id, file_blobs, output_format, quality, max_w, max_h), daemon=True)
  t.start()

  return jsonify({'job_id': job_id, 'total': len(file_blobs)})


@app.route('/status/<job_id>', methods=['GET'])
def job_status(job_id):
  with jobs_lock:
    job = jobs.get(job_id)
    if not job:
      return jsonify({'error': 'Job not found'}), 404
    return jsonify({'total': job['total'], 'processed': job['processed'], 'status': job['status'], 'error': job.get('error'), 'items': job.get('items', [])})


@app.route('/download/<job_id>', methods=['GET'])
def download_job(job_id):
  with jobs_lock:
    job = jobs.get(job_id)
    if not job:
      return Response('Job not found', status=404)
    if job['status'] != 'done' or not job.get('path'):
      return Response('Job not ready', status=400)
    path = job['path']

  # Send the ZIP file
  try:
    return send_file(path, mimetype='application/zip', as_attachment=True, download_name='optimized_images.zip')
  finally:
    # Cleanup after sending
    try:
      os.remove(path)
    except Exception:
      pass
    with jobs_lock:
      jobs.pop(job_id, None)


if __name__ == '__main__':
    # Run development server on port 8000
    # For production use a WSGI server like gunicorn or waitress
    app.run(host='127.0.0.1', port=8000, debug=True)