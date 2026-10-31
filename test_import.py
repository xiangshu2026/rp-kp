import sys, zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import doc_import as di

tmp = Path(__file__).resolve().parent / "_t"
tmp.mkdir(exist_ok=True)

# 1. docx
import docx
d = docx.Document()
d.add_heading("第一幕 雨夜城门", level=1)
d.add_paragraph("调查员在雨夜抵达城门，守卫拦住了他们。")
d.add_heading("线索", level=2)
d.add_paragraph("城门内侧有新鲜的抓痕。")
d.save(str(tmp / "t.docx"))
txt, err = di.extract(tmp / "t.docx")
print("DOCX:", "OK" if txt else "FAIL " + str(err))
if txt: print("  含标题标记:", "#" in txt, "| 字数:", len(txt))

# 2. txt
(tmp / "t.txt").write_text("第二幕 井底" + chr(10) + "调查员下井。", encoding="utf-8")
t2, e2 = di.extract(tmp / "t.txt")
print("TXT:", "OK" if t2 else "FAIL", len(t2 or ""))

# 3. 手搓最小 PDF
content = b"BT /F1 12 Tf 72 720 Td (Chapter 1 The Gate) Tj ET"
comp = zlib.compress(content)
objs = []
objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
objs.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
objs.append(b"<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>")
objs.append(b"<< /Length " + str(len(comp)).encode() + b" >>" + chr(10).encode() + b"stream" + chr(10).encode() + comp + chr(10).encode() + b"endstream")
pdf = b"%PDF-1.4" + chr(10).encode()
for i, o in enumerate(objs):
    pdf += str(i + 1).encode() + b" 0 obj" + chr(10).encode() + o + chr(10).encode() + b"endobj" + chr(10).encode()
pdf += b"trailer" + chr(10).encode() + b"<< /Root 1 0 R >>" + chr(10).encode() + b"%%EOF"
(tmp / "t.pdf").write_bytes(pdf)
t3, e3 = di.extract(tmp / "t.pdf")
print("PDF:", "OK" if t3 else "FAIL " + str(e3))
if t3: print("  内容:", repr(t3[:80]))
print("ALL PASS")
