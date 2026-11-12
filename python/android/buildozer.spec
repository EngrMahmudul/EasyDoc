# Buildozer spec for EasyDoc Android APK
# Build on a Linux machine with Java 17 + Android SDK, or in GitHub Actions
# (see .github/workflows/build.yml in the repo root).
#   pip install buildozer cython
#   buildozer android debug
#   # unsigned APK: bin/easydoc-1.0.0-arm64-v8a-debug.apk
#   # for a release APK, add your keystore (see Buildozer docs) and run:
#   buildozer android release
[app]
title = EasyDoc
package.name = easydoc
package.domain = com.mahmudulhasan.easydoc
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt,md
version = 1.0.0
requirements = python3,kivy,pillow,pymupdf,pypdf,python-docx,python-pptx,openpyxl,reportlab,pytesseract,deep-translator
orientation = portrait
fullscreen = 0
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES,CAMERA
android.api = 33
android.minapi = 24
android.arch = arm64-v8a
android.ndk = 25b
p4a.bootstrap = sdl2
[buildozer]
log_level = 2
warn_on_root = 1
