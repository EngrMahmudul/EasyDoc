"""EasyDoc desktop GUI for Windows 10/11.

Developed by Mahmudul Hasan.

A modern, website-style front-end over easydoc.core — the same
33 tools as the EasyDoc web app, with the same look: a dark header
with EasyDoc branding, coloured tool cards grouped by category,
a search box, a file picker, clear options and a progress bar.

Run:  python -m easydoc.gui   (or launch EasyDoc.exe on Windows)
No new dependencies: plain Tkinter/ttk, which ships with Python
on Windows, so PyInstaller --onefile/--windowed builds keep working.
"""
import os
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from easydoc import core  # noqa: E402

# ---------------------------------------------------------------- palette
NAVY = "#1f2a44"
NAVY_LIGHT = "#2b3a5e"
RED = "#e5322d"
RED_DARK = "#c42722"
TEAL = "#0e9f8a"
BLUE = "#2f6fed"
ORANGE = "#f07b1d"
PURPLE = "#7c5cff"
PINK = "#e84393"
GREEN = "#1d9e57"
GREY_BG = "#f3f5f9"
CARD_BG = "#ffffff"
TEXT = "#1f2a44"
MUTED = "#6b7686"
BORDER = "#dfe4ec"

FONT = "Segoe UI"
if sys.platform != "win32":
    FONT = "DejaVu Sans"

# ---------------------------------------------------------------- tools
# (label, tool-id) — same 33 tools as the web app, same ids as before.
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

# tool-id -> (category, icon, colour, short description)
META = {
    "image-to-pdf": ("Create", "🖼️", TEAL, "Turn JPG / PNG images into a PDF"),
    "scan-to-pdf": ("Create", "📷", TEAL, "True black & white scan of notes"),
    "merge": ("Organize", "🔗", BLUE, "Combine PDFs in the order you want"),
    "split": ("Organize", "✂️", BLUE, "Split a PDF into separate pages"),
    "rotate": ("Organize", "🔄", BLUE, "Rotate pages the way you need"),
    "organize": ("Organize", "🗂️", BLUE, "Reorder, delete or duplicate pages"),
    "crop-pdf": ("Organize", "✂️", BLUE, "Trim page margins, or auto-trim"),
    "compare": ("Organize", "🔍", BLUE, "Side-by-side text difference"),
    "compress": ("Optimize", "🗜️", ORANGE, "Shrink to an exact target size"),
    "pdf-to-word": ("Convert", "📝", PURPLE, "PDF → editable Word document"),
    "pdf-to-pptx": ("Convert", "📊", PURPLE, "PDF → PowerPoint slides"),
    "pdf-to-excel": ("Convert", "📈", PURPLE, "PDF tables → Excel spreadsheet"),
    "pdf-to-markdown": ("Convert", "📋", PURPLE, "PDF → Markdown, tables kept"),
    "pdf-to-pdfa": ("Convert", "🏛️", PURPLE, "PDF → PDF/A for archiving"),
    "word-to-pdf": ("Convert", "📄", PURPLE, "Word → PDF, page breaks kept"),
    "pptx-to-pdf": ("Convert", "📊", PURPLE, "PowerPoint → PDF"),
    "excel-to-pdf": ("Convert", "📈", PURPLE, "Excel → PDF"),
    "html-to-pdf": ("Convert", "🌐", PURPLE, "Web page / HTML → PDF"),
    "pdf-to-jpg": ("Convert", "🖼️", PURPLE, "Every PDF page → JPG image"),
    "edit-text": ("Edit", "✏️", PINK, "Add text — drag it anywhere"),
    "edit-image": ("Edit", "🖼️", PINK, "Add an image, crop / cut / trim"),
    "erase": ("Edit", "🧽", PINK, "Permanently erase text from a PDF"),
    "redact": ("Edit", "⬛", PINK, "Black out sensitive text, for good"),
    "watermark": ("Edit", "💧", PINK, "Stamp text over every page"),
    "page-numbers": ("Edit", "🔢", PINK, "Add page numbers, your style"),
    "sign": ("Edit", "✍️", PINK, "Place your signature on a PDF"),
    "crop-trim-image": ("Edit", "✂️", PINK, "Cut / trim an image, then resize"),
    "ocr": ("Edit", "🔤", PINK, "Scanned PDF → searchable text"),
    "protect": ("Security", "🔒", NAVY, "Password-protect a PDF"),
    "unlock": ("Security", "🔓", NAVY, "Remove a PDF password"),
    "repair": ("Security", "🛠️", NAVY, "Repair a damaged PDF"),
    "translate": ("Convert", "🌍", PURPLE, "Translate a PDF, layout kept"),
    "summarize": ("Edit", "✨", PINK, "Short summary of a long PDF"),
}
CATEGORIES = ["All", "Create", "Organize", "Optimize", "Convert", "Edit", "Security"]

FILE_TYPES = [
    ("PDF / images / Office", "*.pdf *.jpg *.jpeg *.png *.webp *.docx *.pptx *.xlsx *.html *.htm *.txt"),
    ("PDF files", "*.pdf"),
    ("Images", "*.jpg *.jpeg *.png *.webp *.bmp *.gif"),
    ("Office / HTML", "*.docx *.pptx *.xlsx *.html *.htm"),
    ("All files", "*.*"),
]


def _parse_pages(text):
    """'1,3,5-7' -> [1, 3, 5, 6, 7]"""
    out = []
    for part in (text or "").replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("EasyDoc — Developed by Mahmudul Hasan")
        self.geometry("1120x840")
        self.minsize(980, 660)
        self.configure(bg=GREY_BG)
        self.files = []
        self.selected = TOOLS[0][1]
        self._results = queue.Queue()
        self._running = False
        self._style()
        self._build_header()
        self._build_toolbar()
        self._build_cards()
        self._build_workbench()
        self._build_footer()
        self._select_tool(self.selected)
        self.bind("<Control-o>", lambda _e: self.pick())
        self.bind("<Control-Return>", lambda _e: self.run())

    # ---------------------------------------------------------------- style
    def _style(self):
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("TFrame", background=GREY_BG)
        st.configure("TLabel", background=GREY_BG, foreground=TEXT,
                     font=(FONT, 10))
        st.configure("Header.TLabel", background=NAVY, foreground="white")
        st.configure("Card.TFrame", background=CARD_BG, relief="flat")
        st.configure("Card.TLabel", background=CARD_BG, foreground=TEXT)
        st.configure("TButton", font=(FONT, 10, "bold"), padding=8,
                     background="#ffffff", foreground=TEXT)
        st.configure("Accent.TButton", background=RED, foreground="white",
                     font=(FONT, 11, "bold"), padding=(18, 10))
        st.map("Accent.TButton",
               background=[("active", RED_DARK), ("disabled", "#e8a19e")])
        st.configure("Ghost.TButton", background=GREY_BG, foreground=NAVY,
                     font=(FONT, 10, "bold"))
        st.configure("TEntry", font=(FONT, 10), padding=6)
        st.configure("TCombobox", font=(FONT, 10), padding=5)
        st.configure("Horizontal.TProgressbar", background=RED,
                     troughcolor="#e6e9f0", thickness=8)
        st.configure("TLabelframe", background=CARD_BG, foreground=NAVY,
                     font=(FONT, 10, "bold"))
        st.configure("TLabelframe.Label", background=CARD_BG,
                     foreground=NAVY, font=(FONT, 10, "bold"))

    # ---------------------------------------------------------------- header
    def _build_header(self):
        hdr = tk.Frame(self, bg=NAVY, height=86)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📄  EasyDoc", bg=NAVY, fg="white",
                 font=(FONT, 26, "bold")).pack(side="left", padx=20, pady=14)
        tk.Label(hdr, text="Every PDF tool you need — in one place",
                 bg=NAVY, fg="#c7d0e4", font=(FONT, 11)).pack(
                     side="left", padx=8, pady=22)
        right = tk.Frame(hdr, bg=NAVY)
        right.pack(side="right", padx=18, pady=16)
        tk.Label(right, text="Developed by Mahmudul Hasan",
                 bg=RED, fg="white", font=(FONT, 10, "bold"),
                 padx=12, pady=6).pack(anchor="e")
        tk.Label(right, text="🔒 100% on-device  •  No limits",
                 bg=NAVY, fg="#c7d0e4", font=(FONT, 9)).pack(anchor="e", pady=4)

    # ---------------------------------------------------------------- toolbar
    def _build_toolbar(self):
        bar = tk.Frame(self, bg=GREY_BG)
        bar.pack(fill="x", padx=16, pady=(12, 4))
        tk.Label(bar, text="Tools", bg=GREY_BG, fg=NAVY,
                 font=(FONT, 14, "bold")).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh_cards())
        search = ttk.Entry(bar, textvariable=self.search_var, width=34)
        search.pack(side="right", padx=(8, 0))
        search.insert(0, "")
        tk.Label(bar, text="🔍 Search", bg=GREY_BG, fg=MUTED,
                 font=(FONT, 10)).pack(side="right")
        self.cat_var = tk.StringVar(value="All")
        cats = ttk.Combobox(bar, textvariable=self.cat_var, width=12,
                            values=CATEGORIES, state="readonly")
        cats.pack(side="right", padx=8)
        cats.bind("<<ComboboxSelected>>", lambda _e: self._refresh_cards())
        tk.Label(bar, text="Category:", bg=GREY_BG, fg=MUTED,
                 font=(FONT, 10)).pack(side="right")

    # ---------------------------------------------------------------- cards
    def _build_cards(self):
        wrap = tk.Frame(self, bg=GREY_BG)
        wrap.pack(fill="both", expand=True, padx=16, pady=4)
        self.canvas = tk.Canvas(wrap, bg=GREY_BG, highlightthickness=0)
        scroll = ttk.Scrollbar(wrap, orient="vertical",
                               command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.cards_frame = tk.Frame(self.canvas, bg=GREY_BG)
        self.canvas.create_window((0, 0), window=self.cards_frame, anchor="nw")
        self.cards_frame.bind(
            "<Configure>",
            lambda _e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfig(
                             self.canvas.find_withtag("all")[0] if False else 1,
                             width=e.width))
        self._card_widgets = {}
        self._refresh_cards()

    def _refresh_cards(self):
        for w in self.cards_frame.winfo_children():
            w.destroy()
        self._card_widgets = {}
        q = (self.search_var.get() or "").strip().lower()
        cat = self.cat_var.get()
        cols = 4
        row = col = 0
        shown = 0
        for label, tool_id in TOOLS:
            category, icon, colour, desc = META.get(
                tool_id, ("Edit", "📄", NAVY, label))
            if cat != "All" and category != cat:
                continue
            if q and q not in label.lower() and q not in desc.lower():
                continue
            card = tk.Frame(self.cards_frame, bg=CARD_BG, bd=1,
                            highlightbackground=BORDER,
                            highlightthickness=1, cursor="hand2")
            card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
            self.cards_frame.grid_columnconfigure(col, weight=1)
            top = tk.Frame(card, bg=colour, height=44)
            top.pack(fill="x")
            top.pack_propagate(False)
            tk.Label(top, text=icon, bg=colour, fg="white",
                     font=(FONT, 18)).pack(side="left", padx=10, pady=6)
            tk.Label(top, text=category.upper(), bg=colour, fg="white",
                     font=(FONT, 8, "bold")).pack(side="right", padx=10)
            tk.Label(card, text=label, bg=CARD_BG, fg=TEXT,
                     font=(FONT, 10, "bold"), wraplength=210,
                     justify="left", anchor="w").pack(
                         fill="x", padx=10, pady=(8, 0))
            tk.Label(card, text=desc, bg=CARD_BG, fg=MUTED,
                     font=(FONT, 9), wraplength=210, justify="left",
                     anchor="w").pack(fill="x", padx=10, pady=(2, 10))
            for widget in (card, top) + tuple(card.winfo_children()):
                widget.bind("<Button-1>",
                            lambda _e, t=tool_id: self._select_tool(t))
            self._card_widgets[tool_id] = card
            col += 1
            if col >= cols:
                col, row = 0, row + 1
            shown += 1
        if shown == 0:
            tk.Label(self.cards_frame, text="No tools match that search.",
                     bg=GREY_BG, fg=MUTED, font=(FONT, 11)).grid(
                         row=0, column=0, padx=10, pady=20)

    def _select_tool(self, tool_id):
        self.selected = tool_id
        for tid, card in self._card_widgets.items():
            card.configure(highlightbackground=RED if tid == tool_id
                           else BORDER, highlightthickness=2 if tid == tool_id
                           else 1)
        label = {tid: lbl for lbl, tid in TOOLS}[tool_id]
        category, _icon, _colour, desc = META.get(
            tool_id, ("Edit", "📄", NAVY, label))
        self.tool_title.config(text=f"{label}  ·  {category}")
        self.tool_desc.config(text=desc + "  —  " + self._hint(tool_id))
        self._update_options(tool_id)

    @staticmethod
    def _hint(tool_id):
        hints = {
            "image-to-pdf": "Pick one or more images.",
            "scan-to-pdf": "Pick a photo of your notes.",
            "merge": "Pick two or more PDFs, in order.",
            "split": "One PDF — every page becomes its own file.",
            "compress": "Set the target size below (default 5 MB).",
            "rotate": "Rotates every page 90° clockwise.",
            "organize": "Type the new page order, e.g. 3,1,2.",
            "watermark": "Type the watermark text below.",
            "page-numbers": "Adds 'Page 1 of N' to every page.",
            "edit-text": "Type the text, then Run — placed at the top of page 1.",
            "edit-image": "Pick the PDF first, then the image.",
            "erase": "Type the exact text to erase below.",
            "sign": "Pick the PDF first, then your signature image.",
            "ocr": "Makes a scanned PDF searchable.",
            "protect": "Type a password below.",
            "unlock": "Type the PDF password below.",
            "repair": "Rebuilds a damaged PDF, cleanly.",
            "pdf-to-jpg": "One folder of JPGs, one per page.",
            "translate": "Pick a language below (default Spanish).",
            "summarize": "Summary appears in the log below.",
            "compare": "Pick two PDFs to compare.",
            "crop-trim-image": "Auto-trims white borders off an image.",
            "crop-pdf": "Auto-trims the margins of every page.",
            "redact": "Type words to black out, comma-separated.",
        }
        return hints.get(tool_id, "Pick a file, then press Run.")

    # ---------------------------------------------------------------- workbench
    def _build_workbench(self):
        wb = ttk.LabelFrame(self, text="  Workbench  ", padding=10)
        wb.pack(fill="x", padx=16, pady=(4, 0))
        self.tool_title = ttk.Label(wb, text="", font=(FONT, 12, "bold"),
                                    foreground=NAVY)
        self.tool_title.pack(anchor="w")
        self.tool_desc = ttk.Label(wb, text="", wraplength=1000,
                                   foreground=MUTED, font=(FONT, 9))
        self.tool_desc.pack(anchor="w", pady=(2, 8))

        files_row = tk.Frame(wb, bg=CARD_BG)
        files_row.pack(fill="x")
        self.file_list = tk.Listbox(files_row, height=3, font=(FONT, 9),
                                    selectmode="extended")
        self.file_list.pack(side="left", fill="x", expand=True)
        btns = tk.Frame(files_row, bg=CARD_BG)
        btns.pack(side="right", padx=(8, 0))
        ttk.Button(btns, text="＋ Add files…", command=self.pick).pack(
            fill="x", pady=2)
        ttk.Button(btns, text="Remove", command=self._remove_selected).pack(
            fill="x", pady=2)
        ttk.Button(btns, text="Clear", command=self._clear_files).pack(
            fill="x", pady=2)

        # options row — shown / hidden per tool
        opts = tk.Frame(wb, bg=CARD_BG)
        opts.pack(fill="x", pady=(8, 0))
        self.opt_frames = {}
        self.text_var = tk.StringVar()
        self.pw_var = tk.StringVar()
        self.target_var = tk.StringVar(value="5")
        self.pages_var = tk.StringVar()
        self.lang_var = tk.StringVar(value="es")
        self._make_opt(opts, "text", "Text:", self.text_var, 46)
        self._make_opt(opts, "password", "Password:", self.pw_var, 20,
                       show="•")
        self._make_opt(opts, "target", "Target size (MB):", self.target_var, 8)
        self._make_opt(opts, "pages", "Pages (e.g. 3,1,2):", self.pages_var, 18)
        lang_frame = tk.Frame(opts, bg=CARD_BG)
        tk.Label(lang_frame, text="Language:", bg=CARD_BG, fg=TEXT,
                 font=(FONT, 9)).pack(side="left")
        self.lang_box = ttk.Combobox(
            lang_frame, textvariable=self.lang_var, width=14,
            values=["es", "bn", "fr", "de", "ar", "hi", "ur", "en"],
            state="readonly")
        self.lang_box.pack(side="left", padx=4)
        self.opt_frames["language"] = lang_frame

        run_row = tk.Frame(wb, bg=CARD_BG)
        run_row.pack(fill="x", pady=(10, 2))
        self.run_btn = ttk.Button(run_row, text="▶  Run", style="Accent.TButton",
                                  command=self.run)
        self.run_btn.pack(side="left")
        ttk.Button(run_row, text="Open output folder",
                   command=self._open_output).pack(side="left", padx=8)
        self.status_var = tk.StringVar(value="Ready — pick a tool and a file.")
        tk.Label(run_row, textvariable=self.status_var, bg=CARD_BG,
                 fg=MUTED, font=(FONT, 9)).pack(side="left", padx=10)
        self.progress = ttk.Progressbar(wb, mode="indeterminate",
                                        style="Horizontal.TProgressbar")
        self.progress.pack(fill="x", pady=(6, 0))
        self.log = tk.Text(wb, height=4, font=(FONT, 9),
                           bg="#f8fafc", fg=TEXT, relief="flat")
        self.log.pack(fill="x", pady=(6, 0))
        self._last_out = None

    def _make_opt(self, parent, key, label, var, width, show=None):
        frame = tk.Frame(parent, bg=CARD_BG)
        tk.Label(frame, text=label, bg=CARD_BG, fg=TEXT,
                 font=(FONT, 9)).pack(side="left")
        entry = ttk.Entry(frame, textvariable=var, width=width)
        if show:
            entry.configure(show=show)
        entry.pack(side="left", padx=4)
        self.opt_frames[key] = frame

    def _update_options(self, tool_id):
        wanted = {
            "compress": ["target"],
            "watermark": ["text"], "edit-text": ["text"],
            "erase": ["text"], "redact": ["text"],
            "protect": ["password"], "unlock": ["password"],
            "organize": ["pages"],
            "translate": ["language"],
        }.get(tool_id, [])
        for key, frame in self.opt_frames.items():
            if key in wanted:
                frame.pack(side="left", padx=(0, 12))
            else:
                frame.pack_forget()

    def _build_footer(self):
        foot = tk.Frame(self, bg=NAVY)
        foot.pack(fill="x", side="bottom")
        tk.Label(foot, text="Developed by Mahmudul Hasan  •  EasyDoc 1.0.0",
                 bg=NAVY, fg="white", font=(FONT, 10, "bold")).pack(
                     side="left", padx=16, pady=8)
        tk.Label(foot, text="Files never leave your device  •  No MB / page / file-count limits",
                 bg=NAVY, fg="#c7d0e4", font=(FONT, 9)).pack(
                     side="right", padx=16, pady=8)

    # ---------------------------------------------------------------- files
    def pick(self):
        paths = filedialog.askopenfilenames(filetypes=FILE_TYPES)
        for p in paths:
            if p not in self.files:
                self.files.append(p)
                self.file_list.insert("end", p)
        if paths:
            self.status_var.set(f"{len(self.files)} file(s) chosen.")

    def _remove_selected(self):
        for idx in reversed(self.file_list.curselection()):
            self.file_list.delete(idx)
            del self.files[idx]

    def _clear_files(self):
        self.files = []
        self.file_list.delete(0, "end")

    def _open_output(self):
        folder = getattr(self, "_last_dir", None)
        if folder and os.path.isdir(folder):
            os.startfile(folder) if sys.platform == "win32" else None
        else:
            messagebox.showinfo("EasyDoc", "Run a tool first — the output "
                                "folder will open from here.")

    def say(self, msg):
        self.log.insert("end", msg + "\n")
        self.log.see("end")

    # ---------------------------------------------------------------- run
    def run(self):
        if self._running:
            return
        if not self.files:
            messagebox.showwarning("EasyDoc", "Choose a file first.")
            return
        tool = self.selected
        files = list(self.files)
        opts = {"text": self.text_var.get(), "password": self.pw_var.get(),
                "target_mb": self.target_var.get(),
                "pages": self.pages_var.get(), "lang": self.lang_var.get()}
        if tool in ("watermark", "edit-text", "erase", "redact") and not opts["text"]:
            messagebox.showwarning("EasyDoc", "Type the text first.")
            return
        if tool in ("protect", "unlock") and not opts["password"]:
            messagebox.showwarning("EasyDoc", "Type a password first.")
            return
        self._running = True
        self.run_btn.configure(state="disabled")
        self.progress.start(12)
        self.status_var.set(
            f"Running { {tid: lbl for lbl, tid in TOOLS}[tool] }…")
        threading.Thread(target=self._worker, args=(tool, files, opts),
                         daemon=True).start()
        self.after(120, self._poll)

    def _poll(self):
        try:
            kind, payload = self._results.get_nowait()
        except queue.Empty:
            self.after(120, self._poll)
            return
        self.progress.stop()
        self.run_btn.configure(state="normal")
        self._running = False
        if kind == "ok":
            self.status_var.set("Done ✓")
            self.say(f"Done → {payload}")
            messagebox.showinfo("EasyDoc", f"Done:\n{payload}")
        else:
            self.status_var.set("Error — see log.")
            self.say(f"ERROR: {payload}")
            messagebox.showerror("EasyDoc", str(payload))

    def _worker(self, tool, files, opts):
        try:
            out = self._run_tool(tool, files, opts)
            self._results.put(("ok", out))
        except Exception as exc:  # noqa: BLE001 — show it in the UI
            self._results.put(("err", exc))

    # -- every tool, wired to core.py with the same defaults as the CLI --
    def _run_tool(self, tool, files, opts):
        src = files[0]
        stem = Path(src).stem
        outdir = str(Path(src).parent)
        self._last_dir = outdir
        out = os.path.join(outdir, stem + "-easydoc.pdf")
        if tool == "image-to-pdf":
            out = os.path.join(outdir, stem + ".pdf")
            return core.image_to_pdf(files, out)
        if tool == "scan-to-pdf":
            out = os.path.join(outdir, stem + "-scan.pdf")
            return core.scan_to_pdf(files, out, mode="bw")
        if tool == "merge":
            out = os.path.join(outdir, "merged.pdf")
            return core.merge_pdfs(files, out)
        if tool == "split":
            return ", ".join(core.split_pdf(src, outdir))
        if tool == "compress":
            out = os.path.join(outdir, stem + "-compressed.pdf")
            target = None
            try:
                target = int(float(opts["target_mb"]) * 1_000_000)
            except (TypeError, ValueError):
                target = None
            _, rep = core.compress_pdf(src, out, target_bytes=target)
            return f"{out}  ({rep})"
        if tool == "rotate":
            out = os.path.join(outdir, stem + "-rotated.pdf")
            return core.rotate_pdf(src, out)
        if tool == "organize":
            order = _parse_pages(opts["pages"])
            if not order:
                raise ValueError("Type the new page order, e.g. 3,1,2")
            out = os.path.join(outdir, stem + "-organized.pdf")
            return core.organize_pdf(src, out, order)
        if tool == "watermark":
            out = os.path.join(outdir, stem + "-watermarked.pdf")
            return core.watermark_pdf(src, out, opts["text"])
        if tool == "page-numbers":
            out = os.path.join(outdir, stem + "-numbered.pdf")
            return core.add_page_numbers(src, out)
        if tool == "edit-text":
            out = os.path.join(outdir, stem + "-edited.pdf")
            return core.edit_add_text(src, out, opts["text"])
        if tool == "edit-image":
            image = files[1] if len(files) > 1 else None
            if not image:
                picked = filedialog.askopenfilename(
                    filetypes=[("Images", "*.jpg *.jpeg *.png *.webp")])
                if not picked:
                    raise ValueError("Pick an image to add to the PDF.")
                image = picked
            out = os.path.join(outdir, stem + "-edited.pdf")
            return core.edit_add_image(src, out, image)
        if tool == "erase":
            out = os.path.join(outdir, stem + "-erased.pdf")
            _path, count = core.erase_text(src, out, opts["text"])
            return f"{out}  (erased {count} occurrence(s))"
        if tool == "sign":
            image = files[1] if len(files) > 1 else None
            if not image:
                picked = filedialog.askopenfilename(
                    filetypes=[("Signature image", "*.jpg *.jpeg *.png")])
                if not picked:
                    raise ValueError("Pick a signature image.")
                image = picked
            out = os.path.join(outdir, stem + "-signed.pdf")
            return core.sign_pdf(src, out, image)
        if tool == "ocr":
            out = os.path.join(outdir, stem + "-ocr.pdf")
            return core.ocr_pdf(src, out)
        if tool == "protect":
            out = os.path.join(outdir, stem + "-protected.pdf")
            return core.protect_pdf(src, out, opts["password"])
        if tool == "unlock":
            out = os.path.join(outdir, stem + "-unlocked.pdf")
            return core.unlock_pdf(src, out, opts["password"])
        if tool == "repair":
            out = os.path.join(outdir, stem + "-repaired.pdf")
            return core.repair_pdf(src, out)
        if tool == "pdf-to-jpg":
            outdir2 = os.path.join(outdir, stem + "-pages")
            return ", ".join(core.pdf_to_jpg(src, outdir2))
        if tool == "pdf-to-word":
            out = os.path.join(outdir, stem + ".docx")
            return core.pdf_to_word(src, out)
        if tool == "pdf-to-pptx":
            out = os.path.join(outdir, stem + ".pptx")
            return core.pdf_to_pptx(src, out)
        if tool == "pdf-to-excel":
            out = os.path.join(outdir, stem + ".xlsx")
            return core.pdf_to_excel(src, out)
        if tool == "pdf-to-markdown":
            out = os.path.join(outdir, stem + ".md")
            return core.pdf_to_markdown(src, out)
        if tool == "word-to-pdf":
            out = os.path.join(outdir, stem + ".pdf")
            return core.word_to_pdf(src, out)
        if tool == "pptx-to-pdf":
            out = os.path.join(outdir, stem + ".pdf")
            return core.pptx_to_pdf(src, out)
        if tool == "excel-to-pdf":
            out = os.path.join(outdir, stem + ".pdf")
            return core.excel_to_pdf(src, out)
        if tool == "html-to-pdf":
            out = os.path.join(outdir, stem + ".pdf")
            return core.html_to_pdf(src, out)
        if tool == "pdf-to-pdfa":
            out = os.path.join(outdir, stem + "-pdfa.pdf")
            return core.pdf_to_pdfa(src, out)
        if tool == "crop-pdf":
            out = os.path.join(outdir, stem + "-cropped.pdf")
            return core.crop_pdf_pages(src, out)
        if tool == "redact":
            out = os.path.join(outdir, stem + "-redacted.pdf")
            terms = [t.strip() for t in opts["text"].split(",") if t.strip()]
            _path, count = core.redact_pdf(src, out, terms)
            return f"{out}  (redacted {count} occurrence(s))"
        if tool == "translate":
            out = os.path.join(outdir, stem + f"-{opts['lang']}.pdf")
            return core.translate_pdf(src, out, target_lang=opts["lang"])
        if tool == "summarize":
            summary = core.summarize_pdf(src)
            txt = os.path.join(outdir, stem + "-summary.txt")
            Path(txt).write_text(summary, encoding="utf-8")
            return txt
        if tool == "compare":
            if len(files) < 2:
                raise ValueError("Pick two PDFs to compare.")
            txt = os.path.join(outdir, "comparison.txt")
            core.compare_pdfs(files[0], files[1], output=txt)
            return txt
        if tool == "crop-trim-image":
            out = os.path.join(outdir, stem + "-trimmed" + Path(src).suffix)
            return core.crop_trim_image(src, out)
        raise ValueError(f"Unknown tool: {tool}")


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
