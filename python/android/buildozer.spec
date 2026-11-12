# Buildozer spec for EasyDoc Android APK
# Build on a Linux machine with Java 17 + Android SDK, or in GitHub Actions
# (see .github/workflows/build.yml in the repo root).
#   pip install "buildozer==1.5.0" "cython==0.29.36"
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
requirements = python3,kivy,pillow,pymupdf,pypdf,python-docx,python-pptx,openpyxl,pytesseract,deep-translator
orientation = portrait
fullscreen = 0
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES,CAMERA
android.api = 33
android.minapi = 24
android.arch = arm64-v8a
android.ndk = 25b
p4a.bootstrap = sdl2
# python-for-android branch: Buildozer 1.5.0 defaults to master, and
# master is what its current recipes (libffi 3.4.2, hostpython3) are
# tested against. Do NOT use "stable": it still ships libffi 3.2.1,
# far older than the master recipe.
p4a.branch = master
android.accept_sdk_license = True
[buildozer]
log_level = 2
warn_on_root = 1
