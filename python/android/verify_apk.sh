#!/usr/bin/env bash
# verify_apk.sh — fail the build if the EasyDoc APK has the defects
# that crashed 1.0.0 on the Galaxy S21. Run in CI right after
# `buildozer android debug`, e.g.:
#   bash python/android/verify_apk.sh python/android/bin/*.apk
#
# Checks (all must pass):
#   1. The `easydoc` package (core.py) IS inside the APK. In 1.0.0 it
#      was missing entirely (Buildozer only packages source.dir),
#      so `from easydoc import core` raised ModuleNotFoundError and
#      the app died before showing any UI.
#   2. No bundled native library is an x86-64 (or 32-bit) binary.
#      In 1.0.0, PyMuPDF's _mupdf.so/_extra.so/_features.so and
#      chardet's mypyc .so files were glibc-linked x86-64 binaries
#      from the host pip wheel — unloadable on an arm64 phone.
#      (PyMuPDF is no longer in the Android requirements at all;
#      this check guards every other dependency the same way.)
#   3. Reports the bundled CPython / Kivy versions for the build log.
set -u
APK="${1:-}"
if [ -z "$APK" ] || [ ! -f "$APK" ]; then
  echo "verify_apk: usage: $0 <apk-file>" >&2
  exit 2
fi
echo "verify_apk: checking $APK"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
unzip -q -o "$APK" -d "$WORK/apk" || { echo "FAIL: cannot unzip APK"; exit 1; }
FAIL=0

# --- 1. easydoc package must be in the APK -------------------------------
# App source lives in assets/private.tar; the Python bundle (site-
# packages) lives in lib/<abi>/libpybundle.so (gzip-compressed tar).
PRIVATE="$WORK/apk/assets/private.tar"
if [ -f "$PRIVATE" ]; then
  if tar -tf "$PRIVATE" | grep -q "easydoc/__init__"; then
    echo "OK: easydoc package is in assets/private.tar"
    tar -tf "$PRIVATE" | grep "easydoc/" | sed 's/^/    /'
  else
    echo "FAIL: easydoc package is MISSING from assets/private.tar"
    echo "  (Buildozer only packages source.dir — the workflow must copy"
    echo "   python/src/easydoc into python/android/ before building.)"
    FAIL=1
  fi
else
  echo "FAIL: assets/private.tar not found in APK"
  FAIL=1
fi

# --- 2. every bundled .so must be AArch64 --------------------------------
BUNDLE="$WORK/pybundle.tar"
if gzip -dc "$WORK/apk/lib/arm64-v8a/libpybundle.so" > "$BUNDLE" 2>/dev/null \
   && tar -tf "$BUNDLE" >/dev/null 2>&1; then
  mkdir -p "$WORK/so"
  tar -xf "$BUNDLE" -C "$WORK/so" 2>/dev/null
  BAD=0
  while IFS= read -r so; do
    machine="$(readelf -h "$so" 2>/dev/null | grep Machine | sed 's/.*Machine: *//')"
    case "$machine" in
      *AArch64*) ;;
      *)
        echo "FAIL: non-arm64 native lib: ${so#$WORK/so/} ($machine)"
        BAD=1
        ;;
    esac
  done < <(find "$WORK/so" -name '*.so')
  if [ "$BAD" -eq 0 ]; then
    echo "OK: all bundled .so files are AArch64"
  else
    echo "  (A host-architecture wheel slipped into the APK via p4a's pip"
    echo "   fallback. The offending package needs a p4a recipe, a pin"
    echo "   to a pure-Python version, or removal from requirements.)"
    FAIL=1
  fi
  echo "--- bundled versions ---"
  tar -tf "$BUNDLE" | grep -E "dist-info/METADATA$" | \
    sed 's|_python_bundle/site-packages/||; s|/METADATA$||' | sort | \
    sed 's/^/    /'
  ls "$WORK/apk/lib/arm64-v8a/" | grep -E "^libpython" | sed 's/^/    bundled: /'
else
  echo "FAIL: lib/arm64-v8a/libpybundle.so is missing or not a gzip tar"
  FAIL=1
fi

if [ "$FAIL" -ne 0 ]; then
  echo "verify_apk: FAILED — see FAIL lines above"
  exit 1
fi
echo "verify_apk: PASSED"
