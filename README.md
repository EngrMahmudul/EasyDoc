# EasyDoc

Developed by Mahmudul Hasan

EasyDoc is a free, privacy-first PDF toolkit in the style of iLovePDF — it runs 100% in the browser, so your files never leave your device.

Open `index.html` in a browser, or install it as a PWA on Android, iOS, or Windows 10/11.

## Tools included (32)

- Image to PDF / JPG to PDF (orientation, page size, margins, fit)
- Merge PDF, Split PDF, Organize PDF, Rotate PDF, Crop PDF
- Compress PDF — quality modes plus target size (under 1 / 2 / 5 / 10 MB or custom), with before/after size and % saved
- PDF to JPG, PDF to Word, PDF to PowerPoint, PDF to Excel
- Word to PDF, PowerPoint to PDF, Excel to PDF
- Edit PDF (text, images, shapes, freehand)
- Watermark, Page Numbers, Protect PDF, Unlock PDF
- PDF to PDF/A, Repair PDF, Redact PDF
- Sign PDF (draw / type / upload) plus signature requests
- Scan to PDF, OCR PDF (on-device, searchable PDF)
- Compare PDF, PDF Forms, HTML to PDF
- AI Summarizer, Translate PDF, PDF to Markdown
- Workflows

## Notes

- PDF processing libraries (pdf-lib, PDF.js, Tesseract, etc.) load from CDNs when the page is opened, so an internet connection is needed on first use.
- This is a client-side web app. A native Android APK and a Windows 10/11 desktop installer are packaged separately from this same code.

## Python version — Android APK & Windows 10/11 .exe

The Python rebuild lives in `python/` — see [python/README.md](python/README.md).

It is the same EasyDoc (33 tools, Developed by Mahmudul Hasan), written in
Python with PyMuPDF, pdf2docx, LibreOffice (Word → PDF with correct page
breaks), Pillow and Tesseract. 21/21 core tests pass on Linux, including
Compress 10.95 MB → 4.89 MB (97.7% of a 5 MB target) and Word → PDF with a
page break and no black bar.

- Android APK: `python/android/` (Kivy + Buildozer)
- Windows .exe: `python/windows/build_windows.bat` (run on a Windows 10/11 PC)
- GitHub Actions (`.github/workflows/build.yml`) builds both the APK and
  the .exe automatically — push a tag like `v1.0.0` or run it manually.
