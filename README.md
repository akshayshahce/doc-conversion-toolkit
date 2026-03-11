# Doc Conversion Toolkit

Doc Conversion Toolkit is a local-first app for converting, compressing, and organizing images and PDFs on your own machine.

It has:
- a React frontend
- a FastAPI backend
- local-only processing
- temporary file cleanup after each request

Your files are not uploaded to a third-party server.

## What this app can do

### Image tools
- Convert images between `PNG`, `JPG/JPEG`, `WEBP`, `BMP`, `TIFF`, `GIF`, and `SVG` where supported
- Resize images
- Compress images with preview-first controls
- Create one PDF from multiple images

### PDF tools
- Convert PDF pages to images
- Compress PDFs
- Merge PDFs
- Split PDFs
- Extract pages
- Rotate pages
- Delete pages
- Reorder pages

## Easiest way to run

This project is designed so a non-technical person can start it with one command or by double-clicking a file.

### On macOS

1. Download or unzip the project folder.
2. Open the project folder.
3. Double-click [`start.command`]

If macOS blocks it the first time:

1. Right-click `start.command`
2. Click `Open`
3. Click `Open` again

### On Windows

1. Download or unzip the project folder.
2. Open the project folder.
3. Double-click [`start.bat`]

## What the startup script does

The startup script tries to do everything automatically:

1. Check if required tools are installed
2. Install missing system tools when possible
3. Create a local Python virtual environment
4. Install Python packages
5. Install Node.js packages
6. Build the frontend
7. Start the local server
8. Open the app in your browser

The app runs at:

- [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Important note about first-time setup

If a computer has nothing installed yet, the script will try to install what is missing.

### On macOS

`start.command` will try to install:
- Homebrew, if missing
- Python 3, if missing
- Node.js 22, if missing or too old

### On Windows

`start.bat` will try to install:
- Python 3.11, if missing
- Node.js LTS, if missing or too old

This means the script can work for many non-technical users, but there are still real machine-level requirements:

- internet connection is required
- the computer may ask for system permission or password
- corporate or locked-down laptops may block software installation
- first run may take several minutes

That is normal.

## If you already have Python, Node, and a virtual environment

You can still use the same startup file:

### macOS

```bash
start.command
```

### Windows

```bat
start.bat
```

The script will still:
- activate or create `.venv`
- install required packages
- build the frontend
- start the app

## Manual run only if needed

Most users should use the startup script above.

Use manual commands only if you want more control.

### Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### Frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

### Run the app

```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Then open:

- [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Project structure

```text
backend/
  app/
    api/routes/
    core/
    schemas/
    services/
    utils/
frontend/
  src/
    components/
    lib/
```

## Privacy-first behavior

- Files are processed locally on your machine
- The app does not require cloud upload
- Temporary working files are cleaned automatically
- No permanent storage is required for normal processing

## Testing

### Backend tests

```bash
pip install -r backend/requirements-dev.txt
pytest -q backend/tests/test_api_smoke.py
```

### Frontend production build

```bash
cd frontend
npm run build
```

## Limitations

- Very large files can take time and memory
- PDF compression is best-effort, not magic
- Image compression results depend on the original file format and how optimized it already is
- Some fresh machines may require password approval during automatic dependency installation

## Recommended usage for non-technical users

If you want the simplest experience:

1. Download the folder
2. Double-click `start.command` on macOS or `start.bat` on Windows
3. Wait for setup to complete
4. Use the app in the browser

That is the main supported workflow.
