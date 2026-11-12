# Buildozer spec for EasyDoc Android APK
# Build on a Linux machine with Java 17 + Android SDK, or in GitHub Actions
# (see .github/workflows/build.yml in the repo root).
#   pip install "buildozer==1.6.0" "cython==0.29.36"
#   buildozer android debug
#   # unsigned APK: bin/easydoc-1.0.1-arm64-v8a-debug.apk
#   # for a release APK, add your keystore (see Buildozer docs) and run:
#   # buildozer android release
#
# CRASH FIXES (Nov 2026, Galaxy S21 — the 1.0.0 APK crashed on launch):
#  1. The easydoc package was NEVER inside the APK. Buildozer only
#     packages source.dir (python/android/); core.py lives in
#     ../src, and main.py's `../src` path does not exist on a phone,
#     so `from easydoc import core` raised ModuleNotFoundError before
#     any UI appeared. The CI workflow now copies python/src/easydoc
#     into python/android/easydoc before running Buildozer, and the
#     APK-verification step fails the build if easydoc is missing.
#  2. PyMuPDF is REMOVED from the Android requirements on purpose.
#     p4a has no PyMuPDF recipe, so pip fell back to the host wheel:
#     the bundled _mupdf.so/_extra.so were glibc-linked x86-64
#     binaries (readelf: "Advanced Micro Devices X86-64", NEEDED
#     libc.so.6 / libstdc++.so.6 / libmupdfcpp.so.28.6) that can
#     never load on an arm64 Android phone — a second fatal startup
#     crash. Even a correct aarch64 manylinux wheel cannot load on
#     Android (no glibc). A real fix needs a from-source MuPDF build
#     against the NDK (a p4a recipe); until then, core.py guards the
#     fitz import and Image/Scan/Merge/Split/Rotate run on
#     Pillow/pypdf fallbacks.
#  3. Python/Kivy are PINNED. Unpinned, p4a (master) built CPython
#     3.14 (libpython3.14.so was in the APK) with Kivy 2.3.1, which
#     supports Python 3.8-3.13 only — a known crash-on-open cause.
#     3.11.9 is the most widely validated Python for Kivy 2.3.1.
#  4. chardet==5.2.0 is pure Python. The transitive chardet 7.7.0
#     that crept into the 1.0.0 bundle ships mypyc-compiled x86-64
#     .so files — same arch-mismatch crash class, for any code path
#     that imports it.
#  5. numpy (p4a recipe exists) makes Scan-to-PDF fast; without it
#     core.py falls back to a pure-Python per-pixel loop.
#  6. pdf2docx was missing from the APK entirely, so PDF -> Word
#     always failed at runtime. It is pure Python, so it is safe here.
[app]
title = EasyDoc
package.name = easydoc
package.domain = com.mahmudulhasan.easydoc
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt,md
version = 1.0.1
requirements = python3==3.11.9,hostpython3==3.11.9,kivy==2.3.1,android,numpy,pillow,pypdf,python-docx,python-pptx,openpyxl,pytesseract,deep-translator,pdf2docx,chardet==5.2.0
orientation = portrait
fullscreen = 0
# Android 13+ ignores READ_EXTERNAL_STORAGE and denies
# WRITE_EXTERNAL_STORAGE (scoped storage). File picking uses the
# system picker (SAF), which needs no storage permission. INTERNET
# is needed for Translate PDF; media permissions cover gallery files.
android.permissions = INTERNET,READ_MEDIA_IMAGES,READ_MEDIA_VIDEO,READ_MEDIA_AUDIO,CAMERA
# Target API 34 (Android 14). The S21 runs Android 14/15 (One UI 6/7);
# targeting 33 was usable sideloaded but is behind current requirements.
android.api = 34
android.minapi = 24
android.arch = arm64-v8a
android.ndk = 25b
p4a.bootstrap = sdl2

# python-for-android branch: Buildozer 1.6.0 defaults to master, and
# master is what its current recipes (libffi 3.4.2, hostpython3) are
# tested against. Do NOT use "stable": it still ships libffi 3.2.1,
# far older than the master recipe.
p4a.branch = master
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
