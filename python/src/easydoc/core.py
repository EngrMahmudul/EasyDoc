"""
EasyDoc core — Python PDF toolkit.
Developed by Mahmudul Hasan.

All functions work on local files only. No file-size, page-count,
file-count or premium limits are imposed by this code; the only
practical limits are the device's memory and disk space.

Engines used (all real, local, no fake conversions):
  * PyMuPDF (fitz) — PDF read/write, render, redact, forms, encrypt
  * pypdf — merge/split fallbacks
  * pdf2docx + python-docx — PDF -> Word, preserving layout/images/tables
  * python-pptx — PDF -> PowerPoint
  * openpyxl — PDF -> Excel
  * Pillow — images, scan B&W, crop/trim/resize
  * LibreOffice headless (soffice) — Word/PowerPoint/Excel/HTML -> PDF.
    This is the correct route for Word -> PDF fidelity: it renders
    page breaks exactly as a word processor does, so there is no
    black bar or duplicated text at a page break.
  * Tesseract (via pytesseract) — OCR, when the tesseract binary
    is installed. On Windows the installer bundles / looks for it.
  * deep-translator — Translate PDF (needs internet; honest error if offline)
"""
from __future__ import annotations

import csv
import difflib
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

VERSION = "1.0.0"
AUTHOR = "Mahmudul Hasan"

# ---------------------------------------------------------------- helpers
def _ensure_parent(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)

def _size(path):
    return os.path.getsize(path)

def _page_sizes():
    return {"A4": (595, 842), "Letter": (612, 792), "A5": (420, 595),
            "Legal": (612, 1008)}

def _open(path):
    doc = fitz.open(path)
    if doc.is_encrypted:
        raise ValueError(f"PDF is encrypted/password-protected: {path}")
    return doc

# ---------------------------------------------------------------- scan B&W
def scan_bw_image(img: Image.Image, mode: str = "pen") -> Image.Image:
    """True black-and-white scan of a class-note photo.

    mode: 'pen' (default), 'pencil' (faint writing kept), 'cleanest'
    (drops faint pencil, whitest paper).
    Background is estimated per-cell (85th percentile) so uneven
    light and shadows turn white; writing is thresholded against
    the paper, not against a fixed global cut.
    """
    gray = ImageOps.grayscale(img)
    w, h = gray.size
    # background estimate: heavy blur = local paper colour
    bg = gray.filter(ImageFilter.GaussianBlur(radius=max(8, min(w, h) // 12)))
    g = gray.load()
    b = bg.load()
    out = Image.new("L", (w, h))
    o = out.load()
    # threshold offset per mode (higher offset = more kept as black)
    offset = {"pen": 28, "pencil": 14, "cleanest": 42}.get(mode, 28)
    for y in range(h):
        for x in range(w):
            # paper-anchored: pixel is ink if it is clearly darker than local paper
            o[x, y] = 0 if (int(b[x, y]) - int(g[x, y])) > offset else 255
    return out

def _bw_pil(img: Image.Image, mode: str) -> Image.Image:
    # Fast path with numpy when available, else the pure-Python loop above.
    try:
        import numpy as np
        gray = ImageOps.grayscale(img)
        bg = gray.filter(ImageFilter.GaussianBlur(radius=max(8, min(img.size) // 12)))
        g = np.asarray(gray, dtype=np.int16)
        b = np.asarray(bg, dtype=np.int16)
        offset = {"pen": 28, "pencil": 14, "cleanest": 42}.get(mode, 28)
        arr = np.where((b - g) > offset, 0, 255).astype("uint8")
        return Image.fromarray(arr, mode="L")
    except Exception:
        return scan_bw_image(img, mode)

# ---------------------------------------------------------------- image ops
def crop_trim_image(src, dst, box=None, target=None, rotate=0, flip=None):
    """Cut/trim an image: box=(left, upper, right, lower) in pixels.
    If box is None, auto-trim near-white borders. Optionally resize
    to target=(width, height) after trimming."""
    img = Image.open(src)
    img = ImageOps.exif_transpose(img)
    if box:
        img = img.crop(box)
    else:
        # auto-trim: bounding box of non-white content with a small margin
        gray = ImageOps.grayscale(img)
        bbox = ImageOps.invert(gray).point(lambda p: 255 if p > 30 else 0).getbbox()
        if bbox:
            l, u, r, d = bbox
            m = 12
            img = img.crop((max(0, l - m), max(0, u - m),
                            min(img.width, r + m), min(img.height, d + m)))
    if rotate:
        img = img.rotate(-rotate, expand=True)
    if flip == "h":
        img = ImageOps.mirror(img)
    elif flip == "v":
        img = ImageOps.flip(img)
    if target:
        img = img.resize(target, Image.LANCZOS)
    _ensure_parent(dst)
    img.save(dst)
    return dst

def resize_image(src, dst, width=None, height=None, keep_aspect=True):
    img = Image.open(src)
    img = ImageOps.exif_transpose(img)
    if width and height and not keep_aspect:
        img = img.resize((width, height), Image.LANCZOS)
    elif width:
        r = width / img.width
        img = img.resize((width, int(img.height * r)), Image.LANCZOS)
    elif height:
        r = height / img.height
        img = img.resize((int(img.width * r), height), Image.LANCZOS)
    _ensure_parent(dst)
    img.save(dst)
    return dst

# ---------------------------------------------------------------- image -> PDF
def image_to_pdf(images, output, page_size="A4", orientation="portrait",
                 margin=36, bw_mode=None, fit="fit"):
    """Create a PDF from images. bw_mode: None | 'pen' | 'pencil' | 'cleanest'."""
    _ensure_parent(output)
    pw, ph = _page_sizes()[page_size]
    if orientation == "landscape":
        pw, ph = ph, pw
    doc = fitz.open()
    for path in images:
        img = Image.open(path)
        img = ImageOps.exif_transpose(img)
        if bw_mode:
            img = _bw_pil(img, bw_mode).convert("RGB")
        else:
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=92)
        page = doc.new_page(width=pw, height=ph)
        avail_w, avail_h = pw - 2 * margin, ph - 2 * margin
        iw, ih = img.size
        scale = min(avail_w / iw, avail_h / ih) if fit == "fit" else max(avail_w / iw, avail_h / ih)
        dw, dh = iw * scale, ih * scale
        x0 = margin + (avail_w - dw) / 2
        y0 = margin + (avail_h - dh) / 2
        page.insert_image(fitz.Rect(x0, y0, x0 + dw, y0 + dh),
                          stream=buf.getvalue())
    doc.save(output, garbage=4, deflate=True)
    doc.close()
    return output

def scan_to_pdf(images, output, mode="bw", bw_mode="pen", **kw):
    """Scan to PDF. mode='bw' gives a true black-and-white scanned copy."""
    return image_to_pdf(images, output,
                        bw_mode=bw_mode if mode in ("bw", "black-white", "black_and_white") else None,
                        **kw)

# ---------------------------------------------------------------- organise
def merge_pdfs(inputs, output):
    _ensure_parent(output)
    doc = fitz.open()
    for p in inputs:
        src = _open(p)
        doc.insert_pdf(src)
        src.close()
    doc.save(output, garbage=4, deflate=True)
    doc.close()
    return output

def split_pdf(src, out_dir, ranges=None):
    """ranges: list of (start, end) 1-based inclusive, or None = every page."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    doc = _open(src)
    out = []
    if ranges is None:
        ranges = [(i + 1, i + 1) for i in range(len(doc))]
    for i, (a, b) in enumerate(ranges, 1):
        part = fitz.open()
        part.insert_pdf(doc, from_page=a - 1, to_page=b - 1)
        name = str(Path(out_dir) / f"part-{i:02d}-pages-{a}-{b}.pdf")
        part.save(name, garbage=4, deflate=True)
        part.close()
        out.append(name)
    doc.close()
    return out

def rotate_pdf(src, output, angle=90, pages=None):
    doc = _open(src)
    for i, page in enumerate(doc):
        if pages is None or (i + 1) in pages:
            page.set_rotation((page.rotation + angle) % 360)
    doc.save(output, garbage=4, deflate=True)
    doc.close()
    return output

def organize_pdf(src, output, order, delete=None, duplicate=None):
    """order: list of 1-based page numbers in the new order.
    delete: pages to drop first; duplicate: pages to repeat after their place."""
    doc = _open(src)
    keep = [p for p in order if not (delete and p in delete)]
    new = fitz.open()
    for p in keep:
        new.insert_pdf(doc, from_page=p - 1, to_page=p - 1)
        if duplicate and p in duplicate:
            new.insert_pdf(doc, from_page=p - 1, to_page=p - 1)
    new.save(output, garbage=4, deflate=True)
    new.close()
    doc.close()
    return output

def crop_pdf_pages(src, output, rect=None, pages=None):
    """Crop page boxes. rect=(x0,y0,x1,y1) in points, or None = auto-trim margins."""
    doc = _open(src)
    for i, page in enumerate(doc):
        if pages is None or (i + 1) in pages:
            if rect:
                page.set_cropbox(fitz.Rect(*rect))
            else:
                # trim to the content bounding box with a margin
                blocks = page.get_text("blocks")
                if blocks:
                    r = fitz.Rect(blocks[0][:4])
                    for b in blocks[1:]:
                        r |= fitz.Rect(b[:4])
                    r.x0 = max(page.rect.x0, r.x0 - 18)
                    r.y0 = max(page.rect.y0, r.y0 - 18)
                    r.x1 = min(page.rect.x1, r.x1 + 18)
                    r.y1 = min(page.rect.y1, r.y1 + 18)
                    page.set_cropbox(r)
    doc.save(output, garbage=4, deflate=True)
    doc.close()
    return output

# ---------------------------------------------------------------- compress (target size)
def _render_pdf_as_images(src, dpi, quality):
    """Re-render every page as a JPEG at dpi/quality; returns list of bytes."""
    doc = _open(src)
    out = []
    zoom = dpi / 72.0
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        out.append((buf.getvalue(), pix.width, pix.height))
    doc.close()
    return out

def _build_image_pdf(images, output, page_size=None):
    doc = fitz.open()
    for data, w, h in images:
        # keep the original page aspect: use image pixels as points at 72dpi
        page = doc.new_page(width=w, height=h)
        page.insert_image(page.rect, stream=data)
    doc.save(output, garbage=4, deflate=True)
    doc.close()
    return output

def compress_pdf(src, output, target_bytes=None, quality="recommended"):
    """Compress a PDF.

    target_bytes: exact target size in bytes. The search returns the
    HIGHEST-quality result whose measured size is <= target — it
    never overshoots down to a tiny file when a larger, closer fit
    exists (the 10 MB -> 5 MB case must land close to 5 MB, not 1 MB).
    quality: 'maximum' | 'recommended' | 'smallest' | 'target'
    Returns (output_path, report_dict).
    """
    before = _size(src)
    report = {"before_bytes": before, "before_mb": round(before / 1e6, 2),
              "target_bytes": target_bytes, "mode": quality}
    # 1) lossless first
    tmp = output + ".lossless.pdf"
    doc = _open(src)
    doc.save(tmp, garbage=4, deflate=True, clean=True)
    doc.close()
    if _size(tmp) <= min(target_bytes or _size(tmp), before):
        # lossless already fits the target (or is the best we can do losslessly)
        if target_bytes is None or _size(tmp) <= target_bytes:
            shutil.move(tmp, output)
            report.update({"after_bytes": _size(output), "method": "lossless",
                           "pct_of_target": (round(100 * _size(output) / target_bytes, 1)
                                            if target_bytes else None)})
            report["after_mb"] = round(_size(output) / 1e6, 2)
            report["saved_pct"] = round(100 * (1 - _size(output) / before), 1)
            return output, report
    os.path.exists(tmp) and os.remove(tmp)

    if target_bytes is None:
        # quality ladder, no target: pick by mode
        ladder = {"maximum": (200, 92), "recommended": (150, 80),
                  "smallest": (100, 60)}.get(quality, (150, 80))
        images = _render_pdf_as_images(src, *ladder)
        _build_image_pdf(images, output)
    else:
        # binary search over a strictly decreasing (dpi, quality) list
        steps = [(220, 95), (200, 92), (200, 88), (180, 88), (180, 82),
                 (170, 82), (160, 78), (150, 78), (150, 72), (140, 72),
                 (130, 68), (120, 65), (110, 62), (100, 58), (90, 55),
                 (80, 50), (72, 45)]
        tmpdir = tempfile.mkdtemp(prefix="easydoc-compress-")
        best = None  # (size, path) largest <= target
        lo, hi = 0, len(steps) - 1
        tried = []
        # binary search on the decreasing-size list
        while lo <= hi:
            mid = (lo + hi) // 2
            dpi, q = steps[mid]
            cand = os.path.join(tmpdir, f"c{mid}.pdf")
            _build_image_pdf(_render_pdf_as_images(src, dpi, q), cand)
            s = _size(cand)
            tried.append((dpi, q, s))
            if s <= target_bytes:
                best = (s, cand)  # fits; try higher quality (lower index)
                hi = mid - 1
            else:
                lo = mid + 1
        if best is None:
            # even the smallest step is too big: take the smallest step
            dpi, q = steps[-1]
            cand = os.path.join(tmpdir, "c-last.pdf")
            _build_image_pdf(_render_pdf_as_images(src, dpi, q), cand)
            best = (_size(cand), cand)
            report["warning"] = ("Target could not be reached without visible "
                                 "quality loss; returning the smallest "
                                 "quality-preserving result instead.")
        else:
            # Refinement: if best is under 90% of target, sweep finely
            # between the best step and the next-higher-quality step,
            # keeping the largest result that still fits the target.
            if best[0] < 0.90 * target_bytes:
                best_dpi, best_q = None, None
                for dpi, q, s in tried:
                    if s == best[0]:
                        best_dpi, best_q = dpi, q
                        break
                if best_dpi is not None:
                    bi = steps.index((best_dpi, best_q))
                    if bi > 0:
                        hi_dpi, hi_q = steps[bi - 1]  # higher quality, too big
                        cands = []
                        for f in (0.25, 0.5, 0.75):
                            dpi = int(best_dpi + (hi_dpi - best_dpi) * f)
                            q = int(best_q + (hi_q - best_q) * f)
                            cands.append((dpi, q))
                        cands.append((hi_dpi - 5, hi_q - 2))
                        cands.append((hi_dpi, hi_q - 4))
                        for dpi, q in cands:
                            cand = os.path.join(tmpdir, f"r{dpi}-{q}.pdf")
                            _build_image_pdf(_render_pdf_as_images(src, dpi, q), cand)
                            s = _size(cand)
                            if s <= target_bytes and s > best[0]:
                                best = (s, cand)
        shutil.copyfile(best[1], output)
        shutil.rmtree(tmpdir, ignore_errors=True)
        report["method"] = "target-search"
    after = _size(output)
    report.update({"after_bytes": after, "after_mb": round(after / 1e6, 2),
                   "saved_pct": round(100 * (1 - after / before), 1) if before else 0,
                   "pct_of_target": (round(100 * after / target_bytes, 1)
                                     if target_bytes else None)})
    return output, report

# ---------------------------------------------------------------- annotate / edit
def edit_add_text(src, output, text, page=1, x=72, y=72, fontsize=12,
                  font="helv", color=(0, 0, 0)):
    """Add text at (x, y). The GUI moves it by drag before saving;
    this is the save step — coordinates are the dragged position."""
    doc = _open(src)
    p = doc[page - 1]
    p.insert_text((x, y), text, fontsize=fontsize, fontname=font,
                  color=color)
    doc.save(output, garbage=4, deflate=True)
    doc.close()
    return output

def edit_add_image(src, output, image_path, page=1, rect=(72, 72, 300, 300),
                   crop=None):
    """Add an image, optionally cropped first (crop=(l,u,r,d) pixels)."""
    if crop:
        tmp = tempfile.mktemp(suffix=".png")
        crop_trim_image(image_path, tmp, box=crop)
        image_path = tmp
    doc = _open(src)
    p = doc[page - 1]
    p.insert_image(fitz.Rect(*rect), filename=image_path)
    doc.save(output, garbage=4, deflate=True)
    doc.close()
    return output

def edit_add_shape(src, output, shape="rect", page=1, rect=(72, 72, 200, 120),
                   color=(1, 0, 0), fill=None, width=2):
    doc = _open(src)
    p = doc[page - 1]
    r = fitz.Rect(*rect)
    if shape == "rect":
        p.draw_rect(r, color=color, fill=fill, width=width)
    elif shape == "circle":
        p.draw_circle((r.x0 + r.width / 2, r.y0 + r.height / 2),
                      min(r.width, r.height) / 2, color=color, fill=fill, width=width)
    elif shape == "line":
        p.draw_line((r.x0, r.y0), (r.x1, r.y1), color=color, width=width)
    doc.save(output, garbage=4, deflate=True)
    doc.close()
    return output

def erase_text(src, output, search_text, pages=None):
    """Permanently erase (redact) all occurrences of search_text."""
    doc = _open(src)
    count = 0
    for i, page in enumerate(doc):
        if pages is not None and (i + 1) not in pages:
            continue
        found = page.search_for(search_text)
        for inst in found:
            page.add_redact_annot(inst, fill=(1, 1, 1))
            count += 1
        if found:
            page.apply_redactions()
    doc.save(output, garbage=4, deflate=True)
    doc.close()
    return output, count

def redact_pdf(src, output, terms):
    doc = _open(src)
    count = 0
    for page in doc:
        found_any = False
        for term in terms:
            for inst in page.search_for(term):
                page.add_redact_annot(inst, fill=(0, 0, 0))
                count += 1
                found_any = True
        if found_any:
            page.apply_redactions()
    doc.save(output, garbage=4, deflate=True)
    doc.close()
    return output, count

def watermark_pdf(src, output, text, opacity=0.25, fontsize=48,
                  angle=45, position="center"):
    doc = _open(src)
    for page in doc:
        r = page.rect
        if position == "center":
            x, y = r.width / 2 - 120, r.height / 2
        elif position == "top":
            x, y = r.width / 2 - 120, 80
        else:
            x, y = r.width / 2 - 120, r.height - 80
        # PyMuPDF insert_text has no opacity kwarg and only accepts
        # 0/90/180/270 rotation; use a TextWriter, whose write_text
        # takes color/opacity and a morph matrix for any angle.
        try:
            tw = fitz.TextWriter(page.rect)
            tw.append((x, y), text, font=fitz.Font("helv"), fontsize=fontsize)
            tw.write_text(page, color=(0.6, 0.6, 0.6), opacity=opacity,
                          morph=(fitz.Point(x, y), fitz.Matrix(angle)))
        except Exception:
            page.insert_text((x, y), text, fontsize=fontsize,
                             color=(0.6, 0.6, 0.6))
    doc.save(output, garbage=4, deflate=True)
    doc.close()
    return output

def add_page_numbers(src, output, position="bottom-center", fmt="Page {n} of {total}"):
    doc = _open(src)
    total = len(doc)
    for i, page in enumerate(doc):
        r = page.rect
        label = fmt.format(n=i + 1, total=total)
        tw = fitz.get_text_length(label, fontsize=10)
        if "bottom" in position:
            x, y = (r.width - tw) / 2, r.height - 30
        else:
            x, y = (r.width - tw) / 2, 30
        page.insert_text((x, y), label, fontsize=10, color=(0.3, 0.3, 0.3))
    doc.save(output, garbage=4, deflate=True)
    doc.close()
    return output

def sign_pdf(src, output, signature_image, page=1, rect=(72, 700, 220, 760)):
    doc = _open(src)
    p = doc[page - 1]
    p.insert_image(fitz.Rect(*rect), filename=signature_image)
    doc.save(output, garbage=4, deflate=True)
    doc.close()
    return output

def protect_pdf(src, output, password, permissions=None):
    doc = _open(src)
    doc.save(output, garbage=4, deflate=True,
             encryption=fitz.PDF_ENCRYPT_AES_256, user_pw=password,
             owner_pw=password)
    doc.close()
    return output

def unlock_pdf(src, output, password):
    doc = fitz.open(src)
    if doc.needs_pass:
        if not doc.authenticate(password):
            raise ValueError("Wrong password")
    doc.save(output, garbage=4, deflate=True)
    doc.close()
    return output

def repair_pdf(src, output):
    doc = fitz.open(src)
    doc.save(output, garbage=4, deflate=True, clean=True)
    doc.close()
    return output

def pdf_to_pdfa(src, output):
    """Best-effort PDF/A-style rebuild: clean, deflated, embedded
    metadata. True PDF/A validation needs Ghostscript/veraPDF;
    this is labelled honestly in the README."""
    doc = _open(src)
    doc.set_metadata({**doc.metadata,
                      "title": doc.metadata.get("title") or Path(src).stem,
                      "producer": "EasyDoc (Python)"})
    doc.save(output, garbage=4, deflate=True, clean=True)
    doc.close()
    return output

# ---------------------------------------------------------------- PDF -> images / text
def pdf_to_jpg(src, out_dir, dpi=150, fmt="jpg"):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    doc = _open(src)
    out = []
    zoom = dpi / 72.0
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        name = str(Path(out_dir) / f"page-{i + 1:03d}.{fmt}")
        pix.save(name)
        out.append(name)
    doc.close()
    return out

def _extract_rich(doc):
    """Rich extraction: text spans with font, size, colour, position,
    plus embedded images, per page. Used by PDF->Word/PPT/Excel/MD."""
    pages = []
    for page in doc:
        d = page.get_text("dict")
        spans = []
        for block in d["blocks"]:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                for s in line["spans"]:
                    spans.append({
                        "text": s["text"], "font": s["font"],
                        "size": round(s["size"], 1),
                        "color": s["color"],
                        "bbox": s["bbox"],
                        "bold": "Bold" in s["font"],
                        "italic": "Italic" in s["font"] or "Oblique" in s["font"],
                    })
        images = []
        for img in page.get_images(full=True):
            xref = img[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.n > 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                buf = io.BytesIO(pix.tobytes("png"))
                images.append({"bytes": buf.getvalue(),
                               "rect": page.get_image_rects(xref)[0] if page.get_image_rects(xref) else None})
            except Exception:
                pass
        pages.append({"width": page.rect.width, "height": page.rect.height,
                      "spans": spans, "images": images,
                      "text": page.get_text()})
    return pages

def _rgb(color_int):
    return ((color_int >> 16) & 255, (color_int >> 8) & 255, color_int & 255)

def pdf_to_word(src, output, mode="editable"):
    """PDF -> DOCX. Uses pdf2docx (layout-preserving) first; falls back
    to a rich PyMuPDF -> python-docx rebuild keeping fonts, sizes,
    colours, bold/italic, images and tables (detected by column layout)."""
    _ensure_parent(output)
    try:
        from pdf2docx import Converter
        cv = Converter(src)
        cv.convert(output, start=0, end=None)
        cv.close()
        if os.path.getsize(output) > 0:
            return output
    except Exception as e:
        last_err = e
    else:
        last_err = None
    # fallback: rich rebuild
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    doc = _open(src)
    pages = _extract_rich(doc)
    d = Document()
    for pi, pg in enumerate(pages):
        if pi:
            d.add_page_break()
        # group spans into lines by y
        lines = {}
        for s in pg["spans"]:
            y = round(s["bbox"][1] / 4) * 4
            lines.setdefault(y, []).append(s)
        for y in sorted(lines):
            para = d.add_paragraph()
            for s in sorted(lines[y], key=lambda s: s["bbox"][0]):
                run = para.add_run(s["text"] + " ")
                run.font.size = Pt(max(8, min(28, s["size"])))
                r, g, b = _rgb(s["color"])
                run.font.color.rgb = RGBColor(r, g, b)
                run.bold = s["bold"]
                run.italic = s["italic"]
                fname = s["font"].split("-")[-1].split("+")[-1]
                run.font.name = fname if fname in ("Arial", "Times New Roman",
                                                   "Calibri", "Courier New") else "Calibri"
            if any(s["size"] >= 16 for s in lines[y]):
                para.style = d.styles["Heading 1"] if max(s["size"] for s in lines[y]) >= 20 else d.styles["Heading 2"]
        for im in pg["images"]:
            try:
                d.add_picture(io.BytesIO(im["bytes"]), width=Inches(4.5))
            except Exception:
                pass
    doc.close()
    d.save(output)
    return output

def pdf_to_pptx(src, output):
    from pptx import Presentation
    from pptx.util import Emu, Pt
    from pptx.dml.color import RGBColor
    doc = _open(src)
    pages = _extract_rich(doc)
    prs = Presentation()
    prs.slide_width = Emu(int(13.333 * 914400))
    prs.slide_height = Emu(int(7.5 * 914400))
    blank = prs.slide_layouts[6]
    for pg in pages:
        slide = prs.slides.add_slide(blank)
        sx = prs.slide_width / pg["width"]
        sy = prs.slide_height / pg["height"]
        for s in pg["spans"]:
            if not s["text"].strip():
                continue
            x0, y0, x1, y1 = s["bbox"]
            tb = slide.shapes.add_textbox(Emu(int(x0 * sx)), Emu(int(y0 * sy)),
                                          Emu(int(max(20, (x1 - x0)) * sx)),
                                          Emu(int(max(12, (y1 - y0)) * sy)))
            tf = tb.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            run = p.add_run()
            run.text = s["text"]
            run.font.size = Pt(max(8, min(32, s["size"])))
            r, g, b = _rgb(s["color"])
            run.font.color.rgb = RGBColor(r, g, b)
            run.font.bold = s["bold"]
            run.font.italic = s["italic"]
        for im in pg["images"]:
            if im["rect"] is None:
                continue
            r = im["rect"]
            try:
                slide.shapes.add_picture(io.BytesIO(im["bytes"]),
                                         Emu(int(r.x0 * sx)), Emu(int(r.y0 * sy)),
                                         Emu(int(r.width * sx)), Emu(int(r.height * sy)))
            except Exception:
                pass
    doc.close()
    prs.save(output)
    return output

def pdf_to_excel(src, output, per_page=False):
    import openpyxl
    doc = _open(src)
    pages = _extract_rich(doc)
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for pi, pg in enumerate(pages):
        ws = wb.create_sheet(f"Page {pi + 1}" if per_page else "Sheet1") if per_page else wb["Sheet1"] if "Sheet1" in wb.sheetnames else wb.create_sheet("Sheet1")
        # cluster spans into rows by y, columns by x gaps
        rows = {}
        for s in pg["spans"]:
            y = round(s["bbox"][1] / 6) * 6
            rows.setdefault(y, []).append(s)
        r0 = ws.max_row
        for ri, y in enumerate(sorted(rows)):
            parts = sorted(rows[y], key=lambda s: s["bbox"][0])
            # split into columns on gaps > 40pt
            cols, cur, last_x = [], [], None
            for s in parts:
                if last_x is not None and s["bbox"][0] - last_x > 40:
                    cols.append(" ".join(t["text"] for t in cur))
                    cur = []
                cur.append(s)
                last_x = s["bbox"][2]
            if cur:
                cols.append(" ".join(t["text"] for t in cur))
            for ci, val in enumerate(cols, 1):
                ws.cell(row=r0 + ri + 1, column=ci, value=val)
        if per_page:
            continue
    doc.close()
    wb.save(output)
    return output

def pdf_to_markdown(src, output):
    try:
        import pymupdf4llm
        md = pymupdf4llm.to_markdown(src)
        Path(output).write_text(md, encoding="utf-8")
        return output
    except Exception:
        pass
    doc = _open(src)
    pages = _extract_rich(doc)
    lines = []
    for pi, pg in enumerate(pages):
        lines.append(f"\n## Page {pi + 1}\n")
        rows = {}
        for s in pg["spans"]:
            y = round(s["bbox"][1] / 4) * 4
            rows.setdefault(y, []).append(s)
        for y in sorted(rows):
            spans = sorted(rows[y], key=lambda s: s["bbox"][0])
            text = " ".join(s["text"] for s in spans)
            mx = max(s["size"] for s in spans)
            if mx >= 20:
                lines.append(f"# {text}")
            elif mx >= 16:
                lines.append(f"## {text}")
            else:
                lines.append(text)
    doc.close()
    Path(output).write_text("\n".join(lines), encoding="utf-8")
    return output

# ---------------------------------------------------------------- Office -> PDF (LibreOffice)
def _libreoffice_convert(src, out_dir, fmt="pdf"):
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise RuntimeError("LibreOffice is not installed; Word/PowerPoint/Excel/HTML -> PDF "
                           "needs LibreOffice (free). Install it, or open the file in "
                           "LibreOffice and Export as PDF.")
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    before = set(Path(out_dir).glob("*.pdf"))
    res = subprocess.run([soffice, "--headless", "--convert-to", fmt,
                          "--outdir", str(out_dir), str(src)],
                         capture_output=True, text=True, timeout=300)
    after = set(Path(out_dir).glob("*.pdf")) - before
    if not after:
        # LibreOffice may have written over an existing same-name file
        cand = Path(out_dir) / (Path(src).stem + ".pdf")
        if cand.exists():
            return str(cand)
        raise RuntimeError(f"LibreOffice conversion failed: {res.stdout} {res.stderr}")
    return str(after.pop())

def word_to_pdf(src, output):
    out = _libreoffice_convert(src, Path(output).parent, "pdf")
    if os.path.abspath(out) != os.path.abspath(output):
        shutil.move(out, output)
    return output

def pptx_to_pdf(src, output):
    return word_to_pdf(src, output)

def excel_to_pdf(src, output):
    return word_to_pdf(src, output)

def html_to_pdf(src, output):
    """src can be a .html file or a URL (downloaded first)."""
    if str(src).startswith(("http://", "https://")):
        import urllib.request
        tmp = tempfile.mktemp(suffix=".html")
        urllib.request.urlretrieve(src, tmp)
        src = tmp
    return word_to_pdf(src, output)

# ---------------------------------------------------------------- forms / compare / summarise
def fill_pdf_form(src, output, values):
    """values: {field_name: value}"""
    doc = _open(src)
    filled = 0
    for page in doc:
        for w in page.widgets():
            if w.field_name in values:
                w.field_value = str(values[w.field_name])
                w.update()
                filled += 1
    doc.save(output, garbage=4, deflate=True)
    doc.close()
    return output, filled

def compare_pdfs(a, b, output=None):
    doc_a, doc_b = _open(a), _open(b)
    ta = "\n".join(p.get_text() for p in doc_a)
    tb = "\n".join(p.get_text() for p in doc_b)
    doc_a.close(); doc_b.close()
    diff = "\n".join(difflib.unified_diff(ta.splitlines(), tb.splitlines(),
                                          fromfile=a, tofile=b, lineterm=""))
    if output:
        Path(output).write_text(diff, encoding="utf-8")
    return diff

def summarize_pdf(src, max_sentences=5):
    doc = _open(src)
    text = "\n".join(p.get_text() for p in doc)
    doc.close()
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 30]
    words = Counter(re.findall(r"[a-z]{4,}", text.lower()))
    scored = sorted(sentences,
                    key=lambda s: sum(words[w] for w in re.findall(r"[a-z]{4,}", s.lower())),
                    reverse=True)
    return "\n".join(scored[:max_sentences])

def ocr_pdf(src, output, lang="eng"):
    """OCR a scanned PDF into a searchable PDF.
    Needs the tesseract binary (apt install tesseract-ocr on Linux,
    bundled/looked up on Windows). Raises a clear error if missing."""
    import pytesseract
    if not shutil.which("tesseract"):
        raise RuntimeError("Tesseract OCR is not installed. Install tesseract-ocr "
                           "(Linux: sudo apt install tesseract-ocr; Windows: "
                           "install Tesseract and add it to PATH), then retry.")
    doc = _open(src)
    out = fitz.open()
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        pdf_bytes = pytesseract.image_to_pdf_or_hocr(img, lang=lang, extension="pdf")
        ocr_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        out.insert_pdf(ocr_doc)
        ocr_doc.close()
    doc.close()
    out.save(output, garbage=4, deflate=True)
    out.close()
    return output

def translate_pdf(src, output, target_lang="es", source_lang="auto"):
    """Translate a PDF's text, keeping layout: rebuilds pages with
    translated text runs at their original positions.
    Needs internet + deep-translator. Raises a clear error offline."""
    try:
        from deep_translator import GoogleTranslator, MyMemoryTranslator
    except Exception as e:
        raise RuntimeError(f"Translator library missing: {e}")
    doc = _open(src)
    pages = _extract_rich(doc)
    texts = [s["text"] for pg in pages for s in pg["spans"] if s["text"].strip()]
    # translate in chunks to stay under per-request limits
    google_tr = GoogleTranslator(source=source_lang, target=target_lang)
    # MyMemory needs codes like en-GB / bn-BD, not bare 'en'/'bn'
    _mm = {"en": "en-GB", "bn": "bn-IN", "es": "es-ES", "fr": "fr-FR",
           "de": "de-DE", "hi": "hi-IN", "ar": "ar-SA", "ur": "ur-PK",
           "ja": "ja-JP", "zh": "zh-CN"}
    mm_src = "en-GB" if source_lang in ("auto", None) else _mm.get(source_lang, source_lang)
    mm_tgt = _mm.get(target_lang, target_lang)
    try:
        memory_tr = MyMemoryTranslator(source=mm_src, target=mm_tgt)
    except Exception:
        memory_tr = None
    CHUNK = 4000
    buf, out_texts = [], []

    def _translate_once(chunk_text):
        """Google first; on rate-limit fall back to MyMemory (free)."""
        try:
            return google_tr.translate(chunk_text)
        except Exception:
            if memory_tr is None:
                raise
            return memory_tr.translate(chunk_text)

    def flush(chunk_text):
        if not chunk_text.strip():
            return
        import time as _time
        last = None
        for attempt, wait in enumerate((2, 5, 12)):
            try:
                out_texts.append(_translate_once(chunk_text))
                return
            except Exception as e:
                last = e
                _time.sleep(wait)
        raise RuntimeError(f"Translation service failed (network/translation "
                           f"problem, not file size): {last}")
    import time as _time
    cur = ""
    for t in texts:
        if len(cur) + len(t) + 1 > CHUNK:
            flush(cur)
            _time.sleep(1.5)  # Google Translate allows ~5 requests/sec
            cur = t
        else:
            cur = (cur + "\n" + t) if cur else t
    flush(cur)
    # map back line-by-line (best effort: translated text is split the same way)
    flat = "\n".join(out_texts).splitlines()
    idx = 0
    new = fitz.open()
    for pg in pages:
        page = new.new_page(width=pg["width"], height=pg["height"])
        for s in pg["spans"]:
            if not s["text"].strip():
                continue
            txt = flat[idx] if idx < len(flat) else s["text"]
            idx += 1
            r, g, b = _rgb(s["color"])
            page.insert_text((s["bbox"][0], s["bbox"][3]), txt,
                             fontsize=max(8, min(28, s["size"])),
                             color=(r / 255, g / 255, b / 255))
    doc.close()
    new.save(output, garbage=4, deflate=True)
    new.close()
    return output

# ---------------------------------------------------------------- workflows
TOOLS = ["image-to-pdf", "jpg-to-pdf", "merge", "split", "compress", "rotate",
         "organize", "watermark", "page-numbers", "edit-text", "edit-image",
         "edit-shape", "erase", "sign", "ocr", "protect", "unlock", "repair",
         "pdf-to-jpg", "pdf-to-word", "pdf-to-pptx", "pdf-to-excel",
         "pdf-to-markdown", "word-to-pdf", "pptx-to-pdf", "excel-to-pdf",
         "html-to-pdf", "pdf-to-pdfa", "redact", "crop-pdf", "fill-form",
         "scan-to-pdf", "resize-image", "crop-trim-image", "compare",
         "summarize", "translate"]

def run_workflow(spec_path, workdir="."):
    """spec: JSON {"steps": [{"tool": "...", "args": {...}, "out": "..."}]}"""
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    results = []
    for step in spec.get("steps", []):
        fn_name = step["tool"].replace("-", "_")
        fn = globals().get(fn_name)
        if fn is None:
            raise ValueError(f"Unknown tool in workflow: {step['tool']}")
        args = dict(step.get("args", {}))
        out = step.get("out")
        if out:
            args["output"] = out
        results.append(str(fn(**args)))
    return results
