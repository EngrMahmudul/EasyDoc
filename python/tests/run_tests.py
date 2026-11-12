"""EasyDoc Python test suite — generates its own test files, runs the
main flows, and writes tests/results.md with measured results.
Run:  .venv/bin/python tests/run_tests.py
"""
import os, sys, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from PIL import Image, ImageDraw
from easydoc import core
import fitz
from docx import Document

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)
results = []
def check(name, ok, detail):
    results.append({"test": name, "ok": bool(ok), "detail": str(detail)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")

# 1. make a photo-like note image
img = Image.new("RGB", (1200, 1600), "white")
d = ImageDraw.Draw(img)
for i, line in enumerate(["Class notes — Ethics", "Data Privacy is important.",
                          "Algorithmic Discrimination must be avoided.",
                          "Intellectual Property belongs to its creator."]):
    d.text((80, 120 + i * 90), line, fill=(20, 20, 20))
img.save(OUT / "note.jpg", quality=92)

# 2. JPG to PDF
p = core.image_to_pdf([str(OUT / "note.jpg")], str(OUT / "note.pdf"))
check("JPG to PDF", Path(p).exists() and fitz.open(p).page_count == 1,
      f"{p} pages={fitz.open(p).page_count}")

# 3. Scan B&W — paper must become white, ink black
bw = core._bw_pil(Image.open(OUT / "note.jpg"), "pen")
px = list(bw.getdata())
white = sum(1 for v in px if v == 255) / len(px)
check("Scan B&W", white > 0.85, f"white pixels {white:.1%}")
core.scan_to_pdf([str(OUT / "note.jpg")], str(OUT / "note-bw.pdf"), mode="bw")
check("Scan to PDF (B&W)", Path(OUT / "note-bw.pdf").exists(), "bw pdf created")

# 4. Big PDF ~10 MB: 5 pages of noisy high-res photos
big = fitz.open()
for i in range(5):
    im = Image.new("RGB", (1600, 2000))
    pix = im.load()
    import random
    random.seed(i)
    for y in range(0, 2000, 7):
        for x in range(0, 1600, 7):
            pix[x, y] = (random.randint(0,255), random.randint(0,255), random.randint(0,255))
    im.save(OUT / f"noise{i}.jpg", quality=95)
    page = big.new_page(width=595, height=842)
    page.insert_image(page.rect, filename=str(OUT / f"noise{i}.jpg"))
big.save(str(OUT / "big.pdf"), garbage=4, deflate=True)
big.close()
big_mb = os.path.getsize(OUT / "big.pdf") / 1e6
print(f"big.pdf = {big_mb:.2f} MB")

# 5. Compress 10 MB -> 5 MB target
t0 = time.time()
out, rep = core.compress_pdf(str(OUT / "big.pdf"), str(OUT / "big-5mb.pdf"),
                             target_bytes=5_000_000)
dt = time.time() - t0
after_mb = rep["after_mb"]
check("Compress 10MB -> 5MB target",
      3.5 <= after_mb <= 5.0,
      f"before {rep['before_mb']} MB -> after {after_mb} MB "
      f"({rep.get('pct_of_target')}% of target) in {dt:.0f}s method={rep.get('method')}")
print(json.dumps(rep, indent=2))

# 6. Word doc with a page break (the reported bug case)
doc = Document()
doc.add_heading("Question:", level=1)
doc.add_paragraph("Match ethical terms: Data Privacy, Algorithmic Discrimination, Intellectual Property.")
doc.add_page_break()
doc.add_heading("Answer:", level=1)
doc.add_paragraph("Data Privacy — protecting personal information. "
                  "Algorithmic Discrimination — unfair treatment by algorithms. "
                  "Intellectual Property — rights over creative work.")
doc.save(str(OUT / "question.docx"))

# 7. Word -> PDF via LibreOffice
try:
    core.word_to_pdf(str(OUT / "question.docx"), str(OUT / "question.pdf"))
    wd = fitz.open(str(OUT / "question.pdf"))
    text = "\n".join(pg.get_text() for pg in wd)
    n_match = text.count("Match ethical terms")
    # black bar check: no page should be mostly black
    black = False
    for pg in wd:
        pix = pg.get_pixmap(dpi=72)
        # count near-black pixels
        samples = pix.samples
        dark = sum(1 for i in range(0, len(samples), 300) if samples[i] < 20 and samples[i+1] < 20 and samples[i+2] < 20)
        if dark > 200:
            black = True
    check("Word to PDF (page break, no black bar)",
          wd.page_count == 2 and n_match == 1 and not black,
          f"pages={wd.page_count} 'Match ethical terms' occurrences={n_match} black-bar={black}")
    wd.close()
except Exception as e:
    check("Word to PDF (page break, no black bar)", False, str(e))

# 8. PDF -> Word retains text
try:
    core.pdf_to_word(str(OUT / "question.pdf"), str(OUT / "question-back.docx"))
    d2 = Document(str(OUT / "question-back.docx"))
    t2 = "\n".join(p.text for p in d2.paragraphs)
    check("PDF to Word retains text", "Match ethical terms" in t2 and "Answer" in t2,
          f"recovered {len(t2)} chars, 'Match ethical terms' present={'Match ethical terms' in t2}")
except Exception as e:
    check("PDF to Word retains text", False, str(e))

# 9. Merge / split / rotate / watermark / page numbers / pdf->jpg
core.merge_pdfs([str(OUT / "note.pdf"), str(OUT / "question.pdf")], str(OUT / "merged.pdf"))
check("Merge PDF", fitz.open(str(OUT / "merged.pdf")).page_count == 3, "3 pages")
parts = core.split_pdf(str(OUT / "merged.pdf"), str(OUT / "split"))
check("Split PDF", len(parts) == 3, f"{len(parts)} parts")
core.rotate_pdf(str(OUT / "note.pdf"), str(OUT / "rotated.pdf"), angle=90)
check("Rotate PDF", fitz.open(str(OUT / "rotated.pdf"))[0].rotation == 90, "rotation 90")
core.watermark_pdf(str(OUT / "note.pdf"), str(OUT / "wm.pdf"), "EasyDoc")
check("Watermark", Path(OUT / "wm.pdf").exists(), "watermarked")
core.add_page_numbers(str(OUT / "note.pdf"), str(OUT / "numbered.pdf"))
check("Page numbers", "Page 1 of 1" in fitz.open(str(OUT / "numbered.pdf"))[0].get_text(), "number present")
jpgs = core.pdf_to_jpg(str(OUT / "note.pdf"), str(OUT / "jpg-out"), dpi=100)
check("PDF to JPG", len(jpgs) == 1 and Path(jpgs[0]).exists(), jpgs)

# 10. PDF -> Excel / PPTX / Markdown
try:
    core.pdf_to_excel(str(OUT / "question.pdf"), str(OUT / "question.xlsx"))
    check("PDF to Excel", Path(OUT / "question.xlsx").exists(), "xlsx created")
except Exception as e:
    check("PDF to Excel", False, str(e))
try:
    core.pdf_to_pptx(str(OUT / "question.pdf"), str(OUT / "question.pptx"))
    check("PDF to PowerPoint", Path(OUT / "question.pptx").exists(), "pptx created")
except Exception as e:
    check("PDF to PowerPoint", False, str(e))
try:
    core.pdf_to_markdown(str(OUT / "question.pdf"), str(OUT / "question.md"))
    md = Path(OUT / "question.md").read_text()
    check("PDF to Markdown", "Match ethical terms" in md, "text in markdown")
except Exception as e:
    check("PDF to Markdown", False, str(e))

# 11. Edit: add movable text, erase, redact
core.edit_add_text(str(OUT / "note.pdf"), str(OUT / "edited.pdf"), "Hello EasyDoc", x=100, y=100)
check("Edit PDF add text", "Hello EasyDoc" in fitz.open(str(OUT / "edited.pdf"))[0].get_text(), "text present")
_, n = core.erase_text(str(OUT / "edited.pdf"), str(OUT / "erased.pdf"), "Hello EasyDoc")
check("Erase text", n >= 1 and "Hello EasyDoc" not in fitz.open(str(OUT / "erased.pdf"))[0].get_text(), f"erased {n}")

# 12. Protect / unlock, image crop-trim, summarise
core.protect_pdf(str(OUT / "note.pdf"), str(OUT / "protected.pdf"), "secret123")
check("Protect PDF", fitz.open(str(OUT / "protected.pdf")).is_encrypted, "encrypted")
core.unlock_pdf(str(OUT / "protected.pdf"), str(OUT / "unlocked.pdf"), "secret123")
check("Unlock PDF", not fitz.open(str(OUT / "unlocked.pdf")).is_encrypted, "unlocked")
core.crop_trim_image(str(OUT / "note.jpg"), str(OUT / "note-cropped.jpg"), box=(50, 50, 1000, 1200))
check("Image Crop/Cut/Trim", Path(OUT / "note-cropped.jpg").exists(), "cropped")
s = core.summarize_pdf(str(OUT / "question.pdf"), max_sentences=2)
check("Summarize PDF", len(s) > 20, s[:80])

passed = sum(1 for r in results if r["ok"])
(ROOT / "results.md").write_text(
    "# EasyDoc Python — test results\n\n"
    f"Passed {passed}/{len(results)} on this VM (Linux, Python 3.12, LibreOffice present).\n\n"
    + "\n".join(f"- [{'x' if r['ok'] else ' '}] **{r['test']}** — {r['detail']}" for r in results)
    + "\n", encoding="utf-8")
print(f"\n{passed}/{len(results)} passed. Results in tests/results.md")
sys.exit(0 if passed == len(results) else 1)
