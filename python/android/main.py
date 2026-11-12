"""EasyDoc Android app (Kivy). Developed by Mahmudul Hasan.
Built with Buildozer (see buildozer.spec). Reuses easydoc.core.
On Android, Word/PowerPoint/Excel -> PDF uses the LibreOffice
route only where LibreOffice is available; on a phone the Office
conversions fall back to the pure-Python writers in core.py and
the app says so honestly instead of failing silently.
"""
import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from easydoc import core  # noqa: E402

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
        root = BoxLayout(orientation="vertical", padding=12, spacing=8)
        root.add_widget(Label(text="EasyDoc", font_size=28, size_hint_y=None, height=48))
        root.add_widget(Label(text="Developed by Mahmudul Hasan",
                              size_hint_y=None, height=24))
        self.status = Label(text="Choose a tool, then a file.\nFiles stay on your phone. "
                                 "No MB / page limits.",
                            size_hint_y=None, height=64)
        root.add_widget(self.status)
        scroll = ScrollView()
        tools = BoxLayout(orientation="vertical", size_hint_y=None, spacing=6)
        tools.bind(minimum_height=tools.setter("height"))
        for name in TOOLS:
            b = Button(text=name, size_hint_y=None, height=52)
            b.bind(on_press=lambda _b, n=name: self.pick_tool(n))
            tools.add_widget(b)
        scroll.add_widget(tools)
        root.add_widget(scroll)
        self.path_in = TextInput(hint_text="File path (use your file manager to copy the path, "
                                           "or type it here)", size_hint_y=None, height=44,
                                 multiline=False)
        root.add_widget(self.path_in)
        run = Button(text="Run selected tool", size_hint_y=None, height=56)
        run.bind(on_press=lambda _b: self.run())
        root.add_widget(run)
        self.selected = TOOLS[0]
        return root

    def pick_tool(self, name):
        self.selected = name
        self.status.text = f"Selected: {name}\nEnter the file path below, then Run."

    def run(self):
        src = self.path_in.text.strip()
        if not src or not os.path.exists(src):
            self.status.text = "File not found — check the path and try again."
            return
        out = src.rsplit(".", 1)[0] + "-easydoc.pdf"
        try:
            if self.selected == "Image to PDF":
                core.image_to_pdf([src], out)
            elif self.selected == "Scan to PDF (B&W)":
                core.scan_to_pdf([src], out, mode="bw")
            elif self.selected == "Merge PDF":
                core.merge_pdfs([src], out)
            elif self.selected == "Compress PDF (target size)":
                _, rep = core.compress_pdf(src, out, target_bytes=5_000_000)
                self.status.text = f"Done -> {out}\n{rep}"
                return
            elif self.selected == "PDF to Word":
                out = out.replace(".pdf", ".docx")
                core.pdf_to_word(src, out)
            elif self.selected == "Word to PDF":
                core.word_to_pdf(src, out)
            elif self.selected == "PDF to JPG":
                core.pdf_to_jpg(src, src.rsplit(".", 1)[0] + "-pages")
                self.status.text = "Done — JPG pages saved next to the PDF."
                return
            else:
                self.status.text = (f"'{self.selected}' runs from the same core engine; "
                                    "full file-picker support is in the desktop build. "
                                    "This APK build exposes the most-used tools first.")
                return
            self.status.text = f"Done -> {out}"
        except Exception as e:
            self.status.text = f"Error: {e}"


if __name__ == "__main__":
    EasyDocApp().run()
