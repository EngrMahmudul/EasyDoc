# EasyDoc Android — Galaxy S21 crash fix (v1.0.1)

## What the user saw
APK 1.0.0 (`easydoc-1.0.0-arm64-v8a-debug.apk`, GitHub Actions run #9)
installed on a Samsung Galaxy S21 and crashed on launch — no UI,
no error message. (S21s run Android 14 / One UI 6 or Android 15 /
One UI 7, their last major update.)

## Root causes — verified from the shipped APK itself, not guessed
The APK was unpacked and inspected (`unzip -l`, `libpybundle.so`
decompressed, `readelf -h` on the native libs, binary
`AndroidManifest.xml` string pool):

1. **The `easydoc` package was not in the APK at all (fatal).**
   `libpybundle.so` (2,173 entries) contains zero `easydoc` entries
   and `assets/private.tar` contains only `main.pyc`. Buildozer
   packages only `source.dir` (`python/android/`); `core.py` lives
   in `python/src/easydoc`, and `main.py`'s `../src` path does not
   exist on a phone. So `from easydoc import core` raised
   `ModuleNotFoundError` before any UI appeared — on every phone,
   not just the S21.
2. **PyMuPDF's native libs were x86-64 glibc binaries (fatal).**
   `pymupdf/_mupdf.so`, `_extra.so`, `_features.so`, `_tgif.so`
   are ELF64 `Advanced Micro Devices X86-64`, needing
   `libc.so.6` / `libstdc++.so.6` / `libmupdfcpp.so.28.6` — none of
   which exist on Android. p4a has no PyMuPDF recipe (confirmed:
   the recipe directory does not exist upstream), so pip fell back
   to the host wheel. Even a correct aarch64 manylinux wheel could
   not load on Android (no glibc). `import fitz` would have been
   the second fatal crash even after fixing (1). Kivy/Pillow/
   pyjnius `.so` files in the same APK are correctly AArch64.
3. **CPython 3.14 + Kivy 2.3.1, both unpinned.** The APK bundles
   `libpython3.14.so` with Kivy 2.3.1, which officially supports
   Python 3.8–3.13 — a known crash-on-open combination.
4. **Contributing (not fatal at launch):**
   - `targetSdkVersion` 33 on a phone running Android 14/15.
   - Permissions asked for dead-on-Android-13+ storage permissions
     (`READ/WRITE_EXTERNAL_STORAGE`) and never requested at runtime;
     file picking was "type the path yourself".
   - No `INTERNET` permission (Translate needs it).
   - `pdf2docx` was absent from the APK, so PDF → Word always
     failed. `chardet 7.7.0` shipped mypyc-compiled x86-64 `.so`
     files — same arch-mismatch crash class for any importer.

## The fix (this patch, v1.0.1)
- **Workflow** (`.github/workflows/build.yml`): copies
  `python/src/easydoc` into `python/android/easydoc` before
  Buildozer runs (ephemeral, in the runner only), and runs
  `python/android/verify_apk.sh` after the build — it fails the
  build if `easydoc` is missing or any bundled `.so` is not
  AArch64. Verified: the script FAILS on the 1.0.0 APK with both
  defects listed.
- **buildozer.spec**: pins `python3==3.11.9`, `hostpython3==3.11.9`,
  `kivy==2.3.1`; **removes `pymupdf`** (cannot work on Android via
  p4a — see above); adds `android` (permissions + file picker),
  `numpy` (fast Scan B&W; p4a recipe exists), `pdf2docx`,
  `chardet==5.2.0` (pure Python); target API 33 → 34; permissions
  `INTERNET, READ_MEDIA_IMAGES/VIDEO/AUDIO, CAMERA`.
- **core.py**: `import fitz` is guarded (`FITZ_AVAILABLE` flag +
  `_require_fitz()`); a missing engine is now a readable error,
  never a startup crash. Image/Scan → PDF use a Pillow-only path,
  Merge/Split/Rotate use pypdf fallbacks — those four tools work
  on Android without PyMuPDF. Compress / PDF→JPG / editing tools
  still need the engine and say so plainly.
- **main.py**: stdlib-only crash-log writer runs before the Kivy
  import (log goes to `easydoc-crash.log` + logcat); engine import
  tries the packaged copy, then `../src`, then shows the error in
  the UI instead of dying; runtime permission request on start;
  system file picker (Storage Access Framework) with manual-path
  fallback; per-tool availability checks in Run.

## What is NOT fixed by this patch
- Full PDF tools (Compress, PDF→JPG, Edit/Redact/Watermark, …) on
  Android need PyMuPDF working on the phone. That requires a
  from-source MuPDF build against the NDK — i.e. writing a p4a
  recipe (the flet `mobile-forge` pymupdf recipe is the closest
  existing reference). That is a separate, larger job; until it
  exists the Android app honestly says those tools need the
  Windows build.
- OCR still needs a Tesseract binary, which is not on a phone;
  `ocr_pdf` already raises a clear error in that case.

## How to verify on the S21 (after the rebuild)
1. Uninstall the old app first (same package name, new version).
2. Install the new APK, open it — the EasyDoc tool list must
   appear. If it still crashes, pull the log:
   `adb logcat -s python` (look for `Traceback`) and check for
   `easydoc-crash.log` in the phone's Download folder.
3. Tap "Choose file…" → pick a photo → Image to PDF → Run.
   A PDF must appear next to the photo.
4. Merge / Split / Rotate on a PDF from Downloads must work.
5. Compress / PDF to JPG must show the "needs the PDF engine"
   message, not crash.
