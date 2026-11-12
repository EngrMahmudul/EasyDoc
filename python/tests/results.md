# EasyDoc Python — test results

Passed 21/21 on this VM (Linux, Python 3.12, LibreOffice present).

- [x] **JPG to PDF** — /home/hatch/workspace/easydoc-python/tests/output/note.pdf pages=1
- [x] **Scan B&W** — white pixels 99.9%
- [x] **Scan to PDF (B&W)** — bw pdf created
- [x] **Compress 10MB -> 5MB target** — before 10.95 MB -> after 4.89 MB (97.7% of target) in 4s method=target-search
- [x] **Word to PDF (page break, no black bar)** — pages=2 'Match ethical terms' occurrences=1 black-bar=False
- [x] **PDF to Word retains text** — recovered 268 chars, 'Match ethical terms' present=True
- [x] **Merge PDF** — 3 pages
- [x] **Split PDF** — 3 parts
- [x] **Rotate PDF** — rotation 90
- [x] **Watermark** — watermarked
- [x] **Page numbers** — number present
- [x] **PDF to JPG** — ['/home/hatch/workspace/easydoc-python/tests/output/jpg-out/page-001.jpg']
- [x] **PDF to Excel** — xlsx created
- [x] **PDF to PowerPoint** — pptx created
- [x] **PDF to Markdown** — text in markdown
- [x] **Edit PDF add text** — text present
- [x] **Erase text** — erased 1
- [x] **Protect PDF** — encrypted
- [x] **Unlock PDF** — unlocked
- [x] **Image Crop/Cut/Trim** — cropped
- [x] **Summarize PDF** — Question:
Match ethical terms: Data Privacy, Algorithmic Discrimination, Intelle

## Extra live checks (same VM)
- [x] **Translate PDF to Spanish** — "Match ethical terms..." translated to Spanish and rebuilt as a PDF (Google rate-limited the shared IP; MyMemory fallback worked)
- [x] **Translate PDF to Bengali** — translated, 115 chars recovered in the output PDF
- [x] **CLI entry point** — `easydoc compress big.pdf --target-mb 5` reproduced 4.89 MB (97.7% of target)
- [ ] **OCR PDF** — NOT tested on this VM: the Tesseract binary was still installing (`apt-get update` stuck >5 min on a slow proxy) when tests ran. The code raises a clear error if Tesseract is missing; install it (see README) before using OCR.
- [ ] **Android APK / Windows .exe** — NOT built on this VM (see README "Build status"): no Java/Android SDK could be installed in the session, and PyInstaller on Linux cannot make a Windows .exe. Use the GitHub Actions workflow (.github/workflows/build.yml) to build both.
