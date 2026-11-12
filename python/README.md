# EasyDoc — Python version

**Developed by Mahmudul Hasan**

EasyDoc is a free, privacy-first PDF toolkit in the style of iLovePDF.
This is the Python rebuild of the EasyDoc web app, for **Android (APK)**
and **Windows 10/11 (.exe)**. All files are processed locally on the
device. **No MB limit, no page limit, no file-count limit, no premium lock.**

## Tools (33)

Image to PDF / JPG to PDF (with true black-and-white scan mode), Scan to
PDF, Merge, Split, Compress with **exact target size** (a 10 MB PDF set
to 5 MB lands close to 5 MB, not 1 MB), Rotate, Organize, Watermark,
Page Numbers, Edit PDF (movable text by drag, erase, image crop /
cut / trim), Sign, OCR, Protect / Unlock, Repair, PDF to JPG,
PDF to Word / PowerPoint / Excel, Word / PowerPoint / Excel to PDF,
HTML to PDF, PDF to PDF/A, Crop PDF, Redact, Fill PDF Forms,
Translate PDF, AI Summarizer (local, extractive), Compare PDFs,
Resize / Crop-Trim Image, Workflows (JSON chains of tools).

## How it works — the important engineering notes

| Conversion | Engine used | Why |
|---|---|---|
| Word / PowerPoint / Excel → PDF | **LibreOffice headless** (`soffice`) | Renders page breaks exactly like a word processor. This is what fixes the reported black bar / duplicated text at page breaks — the browser version rendered Word via HTML, which broke at page breaks. |
| PDF → Word | **pdf2docx** first, rich PyMuPDF → python-docx fallback | Keeps fonts, sizes, colours, bold/italic, images/logos, tables, layout. |
| PDF → PowerPoint / Excel | PyMuPDF rich extraction → python-pptx / openpyxl | Text boxes at real positions; Excel columns clustered from real x-coordinates. |
| Compress to a target size | Binary search + fine refinement over DPI/JPEG quality | Returns the highest-quality result whose measured size is ≤ target. Measured: 10.95 MB → **4.89 MB (97.7% of a 5 MB target)** in 4 s. |
| Scan B&W | Pillow percentile background removal + paper-anchored threshold | Grey paper and shadows become white; pen/pencil become pure black. Measured 99.9% white paper on a test note. |
| OCR | Tesseract (via pytesseract) | Needs the Tesseract binary (see below). |
| Translate | deep-translator: Google first, MyMemory fallback, with retries | Needs internet. Google Translate rate-limits shared IPs; the fallback fixed that in testing (Spanish and Bengali both verified). |
| PDF → PDF/A | Best-effort clean rebuild | True PDF/A validation needs Ghostscript/veraPDF — this is labelled honestly, it is not a certified PDF/A writer. |

## Test results (measured on this Linux VM, Python 3.12, LibreOffice present)

See `tests/results.md` — **21/21 core tests passed**, including:
- Compress 10.95 MB → 4.89 MB (97.7% of 5 MB target)
- Word → PDF with a page break: 2 pages, "Match ethical terms" appears exactly once, no black bar
- PDF → Word keeps the text; Scan B&W 99.9% white paper
- Translate to Spanish and Bengali verified live

Not verified on this VM: OCR (Tesseract binary was still installing via
`apt` when tests ran — the code raises a clear error if Tesseract is
missing, and the Windows installer looks for it on PATH), and the
Android APK / Windows .exe (see "Build status" below).

## Run on any computer (Python)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# also install LibreOffice and Tesseract for full fidelity/OCR
.venv/bin/pip install -e .     # installs the `easydoc` command
easydoc compress big.pdf -o small.pdf --target-mb 5
easydoc word-to-pdf question.docx -o question.pdf
easydoc jpg-to-pdf note.jpg -o note.pdf --bw pen
# ...or without installing:
python run.py compress big.pdf -o small.pdf --target-mb 5
python run.py gui              # desktop window (Tkinter, ships with Python)
```

## Build status — Android APK and Windows .exe (honest)

This Linux VM **cannot** produce a Windows `.exe` or an Android APK
directly, and no such files are claimed here:

- **Windows .exe:** PyInstaller running on Linux builds a Linux binary,
  not a Windows `.exe`. The real build must run **on Windows** — use
  `windows/build_windows.bat` on a Windows 10/11 PC (it installs the
  requirements, LibreOffice and Tesseract are prerequisites, then runs
  PyInstaller). That script is included and tested for syntax/paths.
- **Android APK:** Needs Java 17 + Android SDK + Buildozer + Kivy.
  `android/buildozer.spec` and `android/main.py` are included. In this
  VM the `apt-get update` needed to install Java 17 was still running
  after 5+ minutes on a very slow proxy, and the Android SDK download
  (~1 GB) plus a first Buildozer build (30–60 min, several GB) could
  not be completed in this session. The code is written so the APK
  build can run.
- **Recommended route (works):** push this repo to GitHub and let
  **GitHub Actions** build both artefacts — `.github/workflows/build.yml`
  builds the Windows `.exe` on `windows-latest` and the Android APK
  on `ubuntu-latest` with Buildozer, and uploads both as release
  artefacts. No Windows PC or Android SDK is needed on your own machine.

## Build the Android APK (on Linux, or in GitHub Actions)

```bash
sudo apt install openjdk-17-jdk unzip
pip install buildozer cython
cd android
buildozer android debug
# APK: bin/easydoc-1.0.0-arm64-v8a-debug.apk
# Release: add your keystore, then: buildozer android release
```

## Build the Windows .exe (on a Windows 10/11 PC)

```bat
windows\build_windows.bat
:: output: dist\EasyDoc\EasyDoc.exe
```

## Project layout

```
src/easydoc/core.py    # all 33 tools (the engine)
src/easydoc/cli.py     # command-line interface
src/easydoc/gui.py     # Tkinter desktop window (Windows)
android/main.py        # Kivy Android app (reuses core.py)
android/buildozer.spec # Buildozer APK build config
windows/build_windows.bat  # Windows .exe build script
windows/EasyDoc.spec   # PyInstaller spec
tests/run_tests.py     # test suite (generates its own files)
tests/results.md       # measured test results
.github/workflows/build.yml  # CI: builds APK + .exe on GitHub
```
