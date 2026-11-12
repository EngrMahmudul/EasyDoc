"""EasyDoc Android app (Kivy). Developed by Mahmudul Hasan.
Built with Buildozer (see buildozer.spec). Reuses easydoc.core.

Crash fix (Nov 2026, Galaxy S21) — what was wrong with the 1.0.0 APK:
  1. The easydoc package was NEVER in the APK. Buildozer only
     packages source.dir (this folder); core.py lives in ../src,
     and main.py's `sys.path.insert(0, "../src")` does not exist on
     a phone. `from easydoc import core` raised ModuleNotFoundError
     before any UI appeared. Fix: the CI workflow now copies
     python/src/easydoc into this folder before running Buildozer,
     and this file also tries the ../src fallback for dev runs.
  2. PyMuPDF's native libs in the APK were glibc-linked x86-64
     binaries (p4a has no PyMuPDF recipe; pip fell back to the host
     wheel). They can never load on an arm64 phone, so
     `import fitz` was a second fatal startup crash. Fix: the
     Android build no longer bundles PyMuPDF at all; core.py now
     imports fitz only if it loads, and Image/Scan/Merge/Split/
     Rotate run on Pillow/pypdf fallbacks. Tools that truly need
     PyMuPDF show a clear message instead of crashing.
  3. Python/Kivy were unpinned, so p4a built CPython 3.14 with
     Kivy 2.3.1 (which supports up to Python 3.13). Fixed by
     pinning python3/hostpython3 to 3.11.9 and kivy to 2.3.1.

Whatever still goes wrong at startup is written to
easydoc-crash.log (see _write_crash_log) and printed to logcat,
so the reason is visible instead of a silent "app has stopped".
On a PC, read it with:  adb logcat -s python
"""
import os
import sys
import traceback


def _crash_log_candidates():
    """Writable places for a startup crash log (best effort)."""
    cands = []
    try:
        cands.append(os.path.join(os.path.expanduser("~"),
                                  "easydoc-crash.log"))
    except Exception:
        pass
    for base in (os.getcwd(), "/sdcard/Download",
                 "/storage/emulated/0/Download"):
        try:
            cands.append(os.path.join(base, "easydoc-crash.log"))
        except Exception:
            pass
    return cands


def _write_crash_log(text):
    """Best-effort: persist a startup traceback AND print it (logcat)."""
    try:
        sys.stderr.write(text + "\n")
        sys.stderr.flush()
    except Exception:
        pass
    for path in _crash_log_candidates():
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text + "\n")
            return path
        except Exception:
            continue
    return None


# --- Kivy import: if THIS fails nothing can show a UI, so log it. ---
try:
    from kivy.app import App
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.label import Label
    from kivy.uix.scrollview import ScrollView
    from kivy.uix.textinput import TextInput
except Exception:
    _write_crash_log("EasyDoc failed to start (Kivy import failed):\n"
                     + traceback.format_exc())
    raise

# --- Engine import: packaged copy first, ../src fallback for dev. ---
CORE_ERROR = None
core = None
try:
    from easydoc import core  # packaged copy (CI copies src/easydoc here)
except Exception:
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                        "..", "src"))
        from easydoc import core  # noqa: F401  (dev-layout fallback)
    except Exception as e:  # noqa: F841
        CORE_ERROR = traceback.format_exc()
        _write_crash_log("EasyDoc engine (easydoc.core) failed to load:\n"
                         + CORE_ERROR)
        core = None


def _request_permissions():
    """Ask Android (13+) for the media permissions this app uses.

    No-op on desktop / if the bridge is missing. Never crashes the app.
    On Android 13+ the old READ_EXTERNAL_STORAGE permission is ignored
    by the OS, so we ask for READ_MEDIA_IMAGES/VIDEO/AUDIO instead.
    File picking itself uses the system picker (SAF), which needs no
    storage permission at all.
    """
    try:
        from android.permissions import request_permissions, Permission
        request_permissions([
            Permission.READ_MEDIA_IMAGES,
            Permission.READ_MEDIA_VIDEO,
            Permission.READ_MEDIA_AUDIO,
            Permission.CAMERA,
        ])
    except Exception:
        pass


def _pick_file_saf(on_chosen):
    """Open Android's system file picker (Storage Access Framework).

    Returns True if the picker was launched. If anything about the
    picker is unavailable, returns False and the caller falls back
    to the manual path field. Copies the chosen file into the app's
    cache dir and calls on_chosen(local_path).
    """
    try:
        from jnius import autoclass, jarray
        from android import activity as _activity

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        mActivity = PythonActivity.mActivity
        Intent = autoclass("android.content.Intent")

        def _on_result(_req, result_code, data):
            try:
                if result_code != -1 or data is None:  # RESULT_OK == -1
                    return
                uri = data.getData()
                if uri is None:
                    return
                cr = mActivity.getContentResolver()
                name = "picked-file"
                try:  # keep the original file name when we can
                    cursor = cr.query(uri, None, None, None, None)
                    if cursor is not None:
                        try:
                            idx = cursor.getColumnIndex(
                                "_display_name")
                            if cursor.moveToFirst() and idx >= 0:
                                name = cursor.getString(idx) or name
                        finally:
                            cursor.close()
                except Exception:
                    pass
                cache = mActivity.getCacheDir().getAbsolutePath()
                local = os.path.join(cache, os.path.basename(name))
                istream = cr.openInputStream(uri)
                buf = jarray("b", [0] * 8192)
                with open(local, "wb") as out:
                    while True:
                        n = istream.read(buf)
                        if n == -1:
                            break
                        out.write(bytearray(buf[:n]))
                istream.close()
                on_chosen(local)
            except Exception:
                _write_crash_log("EasyDoc file-picker result failed:\n"
                                 + traceback.format_exc())

        intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
        intent.addCategory(Intent.CATEGORY_OPENABLE)
        intent.setType("*/*")
        _activity.start_activity(intent, _on_result)
        return True
    except Exception:
        return False


# Tools that work in the Android build without PyMuPDF (Pillow/pypdf
# fallbacks in core.py). Everything else needs the PDF engine and
# shows a clear message instead of crashing.
ANDROID_SAFE_TOOLS = {
    "Image to PDF", "Scan to PDF (B&W)", "Merge PDF", "Split PDF",
    "Rotate PDF",
}

TOOLS = [
    "Image to PDF", "Scan to PDF (B&W)", "Merge PDF", "Split PDF",
    "Compress PDF (target size)", "Rotate PDF", "Organize PDF",
    "Watermark", "Page Numbers", "Edit PDF", "Erase", "Sign PDF",
    "OCR PDF", "Protect / Unlock", "PDF to JPG", "PDF to Word",
    "PDF to PowerPoint", "PDF to Excel", "PDF to Markdown",
    "Word to PDF", "PowerPoint to PDF", "Excel to PDF",
    "HTML to PDF", "PDF to PDF/A", "Crop PDF", "Redact PDF",
    "Translate PDF", "Summarize", "Compare PDFs",
    "Resize / Crop-Trim Image", "Workflows",
]


class EasyDocApp(App):
    title = "EasyDoc"

    def build(self):
        _request_permissions()
        root = BoxLayout(orientation="vertical", padding=12, spacing=8)
        root.add_widget(Label(text="EasyDoc", font_size=28,
                              size_hint_y=None, height=48))
        root.add_widget(Label(text="Developed by Mahmudul Hasan",
                              size_hint_y=None, height=24))
        if core is None:
            status = ("Engine failed to load, so no tool can run.\n"
                      "Details were saved to easydoc-crash.log.\n"
                      "Please reinstall the latest APK.")
        elif getattr(core, "FITZ_AVAILABLE", False):
            status = ("Choose a tool, then a file.\nFiles stay on your "
                      "phone. No MB / page limits.")
        else:
            status = ("Choose a tool, then a file.\nFiles stay on your "
                      "phone. No MB / page limits.\n"
                      "Note: this Android build has no PyMuPDF engine, "
                      "so Image/Scan, Merge, Split and Rotate work; "
                      "Compress, PDF to JPG and editing tools need the "
                      "desktop/Windows build for now.")
        self.status = Label(text=status, size_hint_y=None, height=96)
        root.add_widget(self.status)
        scroll = ScrollView()
        tools = BoxLayout(orientation="vertical", size_hint_y=None,
                          spacing=6)
        tools.bind(minimum_height=tools.setter("height"))
        for name in TOOLS:
            b = Button(text=name, size_hint_y=None, height=52)
            b.bind(on_press=lambda _b, n=name: self.pick_tool(n))
            tools.add_widget(b)
        scroll.add_widget(tools)
        root.add_widget(scroll)
        pick = Button(text="📂 Choose file… (system picker)",
                      size_hint_y=None, height=52)
        pick.bind(on_press=lambda _b: self.pick_file())
        root.add_widget(pick)
        self.path_in = TextInput(
            hint_text="…or type a file path here",
            size_hint_y=None, height=44, multiline=False)
        root.add_widget(self.path_in)
        run = Button(text="Run selected tool", size_hint_y=None, height=56)
        run.bind(on_press=lambda _b: self.run())
        root.add_widget(run)
        self.selected = TOOLS[0]
        return root

    def pick_tool(self, name):
        self.selected = name
        safe = name in ANDROID_SAFE_TOOLS
        engine_ok = bool(core is not None
                         and getattr(core, "FITZ_AVAILABLE", False))
        if core is None:
            note = "Engine failed to load — reinstall the latest APK."
        elif not safe and not engine_ok:
            note = ("Needs the PDF engine (PyMuPDF), not in this "
                    "Android build yet — use the Windows build.")
        else:
            note = "Enter the file path below, then Run."
        self.status.text = f"Selected: {name}\n{note}"

    def pick_file(self):
        def _chosen(local_path):
            self.path_in.text = local_path
            self.status.text = f"Picked file:\n{local_path}"

        if not _pick_file_saf(_chosen):
            self.status.text = ("System picker is not available on this "
                                "device.\nType the file path below "
                                "instead, e.g. under Download/.")

    def run(self):
        if core is None:
            self.status.text = ("Engine failed to load. Details saved to "
                                "easydoc-crash.log — please reinstall "
                                "the latest APK.")
            return
        src = self.path_in.text.strip()
        if not src or not os.path.exists(src):
            self.status.text = ("File not found — use 'Choose file…' "
                                "or check the path and try again.")
            return
        engine_ok = getattr(core, "FITZ_AVAILABLE", False)
        if (self.selected not in ANDROID_SAFE_TOOLS and not engine_ok):
            self.status.text = (
                f"'{self.selected}' needs the PDF engine (PyMuPDF), "
                "which is not in this Android build yet.\n"
                "Image/Scan to PDF, Merge, Split and Rotate work here; "
                "for the rest, use the Windows build for now.")
            return
        out = src.rsplit(".", 1)[0] + "-easydoc.pdf"
        try:
            if self.selected == "Image to PDF":
                core.image_to_pdf([src], out)
            elif self.selected == "Scan to PDF (B&W)":
                core.scan_to_pdf([src], out, mode="bw")
            elif self.selected == "Merge PDF":
                core.merge_pdfs([src], out)
            elif self.selected == "Split PDF":
                parts = core.split_pdf(src, src.rsplit(".", 1)[0]
                                       + "-parts")
                self.status.text = ("Done — split into:\n"
                                    + "\n".join(parts))
                return
            elif self.selected == "Rotate PDF":
                core.rotate_pdf(src, out, angle=90)
            elif self.selected == "Compress PDF (target size)":
                _, rep = core.compress_pdf(src, out,
                                           target_bytes=5_000_000)
                self.status.text = f"Done -> {out}\n{rep}"
                return
            elif self.selected == "PDF to Word":
                out = out.replace(".pdf", ".docx")
                core.pdf_to_word(src, out)
            elif self.selected == "Word to PDF":
                core.word_to_pdf(src, out)
            elif self.selected == "PDF to JPG":
                core.pdf_to_jpg(src, src.rsplit(".", 1)[0] + "-pages")
                self.status.text = ("Done — JPG pages saved next to "
                                    "the PDF.")
                return
            else:
                self.status.text = (
                    f"'{self.selected}' is not wired up in this "
                    "Android build yet. Image/Scan to PDF, Merge, "
                    "Split and Rotate work here; the full tool list "
                    "is in the Windows build.")
                return
            self.status.text = f"Done -> {out}"
        except Exception as e:
            # A tool failing must show the reason on screen, never
            # kill the app.
            self.status.text = f"Error: {e}"
            _write_crash_log(f"EasyDoc tool '{self.selected}' failed "
                             f"on {src}:\n" + traceback.format_exc())


if __name__ == "__main__":
    EasyDocApp().run()
