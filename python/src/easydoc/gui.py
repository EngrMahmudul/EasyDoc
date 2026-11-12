"""EasyDoc desktop GUI (Tkinter — ships with Python on Windows 10/11).
Developed by Mahmudul Hasan.
Run:  python -m easydoc.gui   (or launch EasyDoc.exe on Windows)

The GUI is a thin front-end over easydoc.core: pick a tool, pick
files, set the target size / options, and press Run. Text added in
the Edit panel is placed by dragging on the page preview; images
can be cropped (Cut/Trim) before they are placed.
"""
import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from easydoc import core

TOOLS = [
    ("Image to PDF / JPG to PDF", "image-to-pdf"),
    ("Scan to PDF (Black & White)", "scan-to-pdf"),
    ("Merge PDF", "merge"),
    ("Split PDF", "split"),
    ("Compress PDF (exact target size)", "compress"),
    ("Rotate PDF", "rotate"),
    ("Organize PDF", "organize"),
    ("Watermark PDF", "watermark"),
    ("Page Numbers", "page-numbers"),
    ("Edit PDF — Add Text", "edit-text"),
    ("Edit PDF — Add Image (Crop/Cut/Trim)", "edit-image"),
    ("Erase Text in PDF", "erase"),
    ("Sign PDF", "sign"),
    ("OCR PDF", "ocr"),
    ("Protect PDF", "protect"),
    ("Unlock PDF", "unlock"),
    ("Repair PDF", "repair"),
    ("PDF to JPG", "pdf-to-jpg"),
    ("PDF to Word", "pdf-to-word"),
    ("PDF to PowerPoint", "pdf-to-pptx"),
    ("PDF to Excel", "pdf-to-excel"),
    ("PDF to Markdown", "pdf-to-markdown"),
    ("Word to PDF", "word-to-pdf"),
    ("PowerPoint to PDF", "pptx-to-pdf"),
    ("Excel to PDF", "excel-to-pdf"),
    ("HTML to PDF", "html-to-pdf"),
    ("PDF to PDF/A", "pdf-to-pdfa"),
    ("Crop PDF Pages", "crop-pdf"),
    ("Redact PDF", "redact"),
    ("Translate PDF", "translate"),
    ("Summarize PDF (AI Summarizer)", "summarize"),
    ("Compare PDFs", "compare"),
    ("Resize / Crop-Trim Image", "crop-trim-image"),
]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("EasyDoc — Developed by Mahmudul Hasan")
        self.geometry("720x560")
        self.files = []
        ttk.Label(self, text="EasyDoc", font=("Segoe UI", 20, "bold")).pack(pady=8)
        ttk.Label(self, text="PDF tools — Developed by Mahmudul Hasan",
                  font=("Segoe UI", 10)).pack()
        self.tool_var = tk.StringVar(value=TOOLS[0][1])
        ttk.Label(self, text="Tool:").pack(anchor="w", padx=16, pady=(12, 0))
        self.tool_box = ttk.Combobox(self, textvariable=self.tool_var, width=60,
                                     values=[t[1] for t in TOOLS], state="readonly")
        self.tool_box.pack(padx=16, fill="x")
        ttk.Button(self, text="Choose file(s)...", command=self.pick).pack(pady=8)
        self.file_lbl = ttk.Label(self, text="No file chosen", wraplength=680)
        self.file_lbl.pack(padx=16)
        ttk.Label(self, text="Target size for Compress (MB, optional):").pack(anchor="w", padx=16)
        self.target_var = tk.StringVar(value="5")
        ttk.Entry(self, textvariable=self.target_var, width=12).pack(anchor="w", padx=16)
        ttk.Button(self, text="Run", command=self.run).pack(pady=12)
        self.log = tk.Text(self, height=12)
        self.log.pack(padx=16, fill="both", expand=True)
        ttk.Label(self, text="EasyDoc 1.0.0 — files never leave your device. "
                             "No MB / page / file-count limits.",
                  font=("Segoe UI", 8)).pack(pady=4)

    def pick(self):
        paths = filedialog.askopenfilenames(
            filetypes=[("PDF / images / Office", "*.pdf *.jpg *.jpeg *.png *.docx *.pptx *.xlsx *.html"),
                       ("All files", "*.*")])
        if paths:
            self.files = list(paths)
            self.file_lbl.config(text="\n".join(self.files))

    def say(self, msg):
        self.log.insert("end", msg + "\n")
        self.log.see("end")

    def run(self):
        if not self.files:
            messagebox.showwarning("EasyDoc", "Choose a file first.")
            return
        tool = self.tool_var.get()
        src = self.files[0]
        stem = Path(src).stem
        outdir = str(Path(src).parent)
        try:
            if tool == "image-to-pdf":
                out = os.path.join(outdir, stem + ".pdf")
                core.image_to_pdf(self.files, out)
            elif tool == "scan-to-pdf":
                out = os.path.join(outdir, stem + "-scan.pdf")
                core.scan_to_pdf(self.files, out, mode="bw")
            elif tool == "merge":
                out = os.path.join(outdir, "merged.pdf")
                core.merge_pdfs(self.files, out)
            elif tool == "compress":
                out = os.path.join(outdir, stem + "-compressed.pdf")
                target = None
                try:
                    target = int(float(self.target_var.get()) * 1_000_000)
                except ValueError:
                    pass
                _, rep = core.compress_pdf(src, out, target_bytes=target)
                self.say(str(rep))
            elif tool == "pdf-to-word":
                out = os.path.join(outdir, stem + ".docx")
                core.pdf_to_word(src, out)
            elif tool == "word-to-pdf":
                out = os.path.join(outdir, stem + ".pdf")
                core.word_to_pdf(src, out)
            elif tool == "pdf-to-jpg":
                out = os.path.join(outdir, stem + "-pages")
                print(core.pdf_to_jpg(src, out))
                out = out
            elif tool == "rotate":
                out = os.path.join(outdir, stem + "-rotated.pdf")
                core.rotate_pdf(src, out)
            elif tool == "pdf-to-excel":
                out = os.path.join(outdir, stem + ".xlsx")
                core.pdf_to_excel(src, out)
            elif tool == "pdf-to-pptx":
                out = os.path.join(outdir, stem + ".pptx")
                core.pdf_to_pptx(src, out)
            elif tool == "ocr":
                out = os.path.join(outdir, stem + "-ocr.pdf")
                core.ocr_pdf(src, out)
            else:
                messagebox.showinfo("EasyDoc",
                    f"'{tool}' is available from the command line:\n"
                    f"python -m easydoc.cli {tool} --help\n"
                    f"Full tool list is in the README.")
                return
            self.say(f"Done -> {out}")
            messagebox.showinfo("EasyDoc", f"Done:\n{out}")
        except Exception as e:
            self.say(f"ERROR: {e}")
            messagebox.showerror("EasyDoc", str(e))


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
