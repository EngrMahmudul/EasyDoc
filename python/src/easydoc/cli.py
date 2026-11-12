"""EasyDoc command line. Developed by Mahmudul Hasan.
Usage examples:
  python -m easydoc.cli image-to-pdf photo1.jpg photo2.jpg -o out.pdf
  python -m easydoc.cli merge a.pdf b.pdf -o merged.pdf
  python -m easydoc.cli compress in.pdf -o out.pdf --target-mb 5
  python -m easydoc.cli pdf-to-word in.pdf -o out.docx
  python -m easydoc.cli word-to-pdf in.docx -o out.pdf
  python -m easydoc.cli jpg-to-pdf photo.jpg -o out.pdf --bw pen
  python -m easydoc.cli workflow flow.json
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from easydoc import core


def main(argv=None):
    p = argparse.ArgumentParser(prog="easydoc", description="EasyDoc — Python PDF toolkit")
    sub = p.add_subparsers(dest="tool", required=True)

    def add(name, **kw):
        s = sub.add_parser(name, **kw)
        s.add_argument("-o", "--output", required=False)
        return s

    s = add("image-to-pdf"); s.add_argument("images", nargs="+")
    s.add_argument("--page-size", default="A4"); s.add_argument("--orientation", default="portrait")
    s.add_argument("--bw", default=None, help="pen|pencil|cleanest")
    s = add("jpg-to-pdf"); s.add_argument("images", nargs="+")
    s.add_argument("--bw", default=None)
    s = add("merge"); s.add_argument("inputs", nargs="+")
    s = add("split"); s.add_argument("src"); s.add_argument("--ranges", default=None,
        help="e.g. 1-3,5-5")
    s = add("compress"); s.add_argument("src"); s.add_argument("--target-mb", type=float, default=None)
    s.add_argument("--quality", default="recommended")
    s = add("rotate"); s.add_argument("src"); s.add_argument("--angle", type=int, default=90)
    s = add("organize"); s.add_argument("src"); s.add_argument("--order", required=True,
        help="comma list e.g. 3,1,2")
    s = add("watermark"); s.add_argument("src"); s.add_argument("--text", required=True)
    s = add("page-numbers"); s.add_argument("src")
    s = add("edit-text"); s.add_argument("src"); s.add_argument("--text", required=True)
    s.add_argument("--page", type=int, default=1); s.add_argument("--x", type=float, default=72)
    s.add_argument("--y", type=float, default=72); s.add_argument("--size", type=float, default=12)
    s = add("edit-image"); s.add_argument("src"); s.add_argument("--image", required=True)
    s.add_argument("--page", type=int, default=1)
    s.add_argument("--crop", default=None, help="left,upper,right,lower pixels")
    s = add("erase"); s.add_argument("src"); s.add_argument("--text", required=True)
    s = add("redact"); s.add_argument("src"); s.add_argument("--terms", nargs="+", required=True)
    s = add("sign"); s.add_argument("src"); s.add_argument("--image", required=True)
    s = add("ocr"); s.add_argument("src"); s.add_argument("--lang", default="eng")
    s = add("protect"); s.add_argument("src"); s.add_argument("--password", required=True)
    s = add("unlock"); s.add_argument("src"); s.add_argument("--password", required=True)
    s = add("repair"); s.add_argument("src")
    s = add("pdf-to-jpg"); s.add_argument("src"); s.add_argument("--dpi", type=int, default=150)
    s = add("pdf-to-word"); s.add_argument("src")
    s = add("pdf-to-pptx"); s.add_argument("src")
    s = add("pdf-to-excel"); s.add_argument("src")
    s = add("pdf-to-markdown"); s.add_argument("src")
    s = add("word-to-pdf"); s.add_argument("src")
    s = add("pptx-to-pdf"); s.add_argument("src")
    s = add("excel-to-pdf"); s.add_argument("src")
    s = add("html-to-pdf"); s.add_argument("src")
    s = add("pdf-to-pdfa"); s.add_argument("src")
    s = add("crop-pdf"); s.add_argument("src")
    s = add("fill-form"); s.add_argument("src"); s.add_argument("--values", required=True,
        help='JSON e.g. {"Name":"Mahmudul"}')
    s = add("scan-to-pdf"); s.add_argument("images", nargs="+")
    s.add_argument("--bw-mode", default="pen")
    s = add("resize-image"); s.add_argument("src"); s.add_argument("--width", type=int, default=None)
    s = add("crop-trim-image"); s.add_argument("src"); s.add_argument("--box", default=None,
        help="left,upper,right,lower or auto")
    s = add("compare"); s.add_argument("a"); s.add_argument("b")
    s = add("summarize"); s.add_argument("src"); s.add_argument("--sentences", type=int, default=5)
    s = add("translate"); s.add_argument("src"); s.add_argument("--target", default="es")
    s = add("workflow"); s.add_argument("spec")

    a = p.parse_args(argv)
    out = a.output
    t = a.tool
    try:
        if t in ("image-to-pdf", "jpg-to-pdf"):
            core.image_to_pdf(a.images, out, page_size=getattr(a, "page_size", "A4"),
                              orientation=getattr(a, "orientation", "portrait"),
                              bw_mode=getattr(a, "bw", None))
        elif t == "merge":
            core.merge_pdfs(a.inputs, out)
        elif t == "split":
            ranges = None
            if a.ranges:
                ranges = [tuple(map(int, r.split("-"))) for r in a.ranges.split(",")]
            print("\n".join(core.split_pdf(a.src, out or "split", ranges)))
            return 0
        elif t == "compress":
            target = int(a.target_mb * 1_000_000) if a.target_mb else None
            _, rep = core.compress_pdf(a.src, out, target_bytes=target, quality=a.quality)
            print(json.dumps(rep, indent=2))
        elif t == "rotate":
            core.rotate_pdf(a.src, out, angle=a.angle)
        elif t == "organize":
            core.organize_pdf(a.src, out, [int(x) for x in a.order.split(",")])
        elif t == "watermark":
            core.watermark_pdf(a.src, out, a.text)
        elif t == "page-numbers":
            core.add_page_numbers(a.src, out)
        elif t == "edit-text":
            core.edit_add_text(a.src, out, a.text, page=a.page, x=a.x, y=a.y, fontsize=a.size)
        elif t == "edit-image":
            crop = tuple(map(int, a.crop.split(","))) if a.crop else None
            core.edit_add_image(a.src, out, a.image, page=a.page, crop=crop)
        elif t == "erase":
            _, n = core.erase_text(a.src, out, a.text); print(f"erased {n} occurrence(s)")
        elif t == "redact":
            _, n = core.redact_pdf(a.src, out, a.terms); print(f"redacted {n} occurrence(s)")
        elif t == "sign":
            core.sign_pdf(a.src, out, a.image)
        elif t == "ocr":
            core.ocr_pdf(a.src, out, lang=a.lang)
        elif t == "protect":
            core.protect_pdf(a.src, out, a.password)
        elif t == "unlock":
            core.unlock_pdf(a.src, out, a.password)
        elif t == "repair":
            core.repair_pdf(a.src, out)
        elif t == "pdf-to-jpg":
            print("\n".join(core.pdf_to_jpg(a.src, out or "jpg-out", dpi=a.dpi)))
            return 0
        elif t == "pdf-to-word":
            core.pdf_to_word(a.src, out)
        elif t == "pdf-to-pptx":
            core.pdf_to_pptx(a.src, out)
        elif t == "pdf-to-excel":
            core.pdf_to_excel(a.src, out)
        elif t == "pdf-to-markdown":
            core.pdf_to_markdown(a.src, out)
        elif t == "word-to-pdf":
            core.word_to_pdf(a.src, out)
        elif t == "pptx-to-pdf":
            core.pptx_to_pdf(a.src, out)
        elif t == "excel-to-pdf":
            core.excel_to_pdf(a.src, out)
        elif t == "html-to-pdf":
            core.html_to_pdf(a.src, out)
        elif t == "pdf-to-pdfa":
            core.pdf_to_pdfa(a.src, out)
        elif t == "crop-pdf":
            core.crop_pdf_pages(a.src, out)
        elif t == "fill-form":
            _, n = core.fill_pdf_form(a.src, out, json.loads(a.values)); print(f"filled {n} field(s)")
        elif t == "scan-to-pdf":
            core.scan_to_pdf(a.images, out, bw_mode=a.bw_mode)
        elif t == "resize-image":
            core.resize_image(a.src, out, width=a.width)
        elif t == "crop-trim-image":
            box = None if a.box in (None, "auto") else tuple(map(int, a.box.split(",")))
            core.crop_trim_image(a.src, out, box=box)
        elif t == "compare":
            print(core.compare_pdfs(a.a, a.b, out))
            return 0
        elif t == "summarize":
            print(core.summarize_pdf(a.src, max_sentences=a.sentences))
            return 0
        elif t == "translate":
            core.translate_pdf(a.src, out, target_lang=a.target)
        elif t == "workflow":
            print("\n".join(core.run_workflow(a.spec)))
            return 0
        print(f"Done -> {out}")
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
