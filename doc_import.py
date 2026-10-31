# -*- coding: utf-8 -*-
"""文档导入：PDF / DOCX / TXT / MD 提取纯文本。PDF 用纯标准库实现。"""
import re, zlib
from pathlib import Path
NL = chr(10)
BS = chr(92)


def read_docx(path):
    try:
        import docx
    except ImportError:
        return None, "未安装 python-docx"
    try:
        d = docx.Document(str(path))
    except Exception as e:
        return None, "DOCX 打开失败：" + str(e)[:120]
    out = []
    for p in d.paragraphs:
        t = p.text.rstrip()
        if not t:
            continue
        style = (p.style.name or "").lower()
        if "heading" in style or "标题" in style:
            lvl = 2
            m = re.search(r"([0-9])", style)
            if m:
                lvl = min(6, max(1, int(m.group(1))))
            out.append("#" * lvl + " " + t)
        else:
            out.append(t)
    for tbl in d.tables:
        out.append("")
        for row in tbl.rows:
            cells = [c.text.strip().replace(NL, " ") for c in row.cells]
            if any(cells):
                out.append(" | ".join(cells))
    return NL.join(out), None


def read_pdf(path):
    """纯标准库 PDF 文本提取：解压内容流，抽 Tj / TJ 字符串。"""
    try:
        raw = Path(path).read_bytes()
    except Exception as e:
        return None, "读取失败：" + str(e)[:100]
    if not raw.startswith(b"%PDF"):
        return None, "不是 PDF 文件"

    texts = []
    pos = 0
    stream_count = 0
    while True:
        i = raw.find(b"stream", pos)
        if i < 0:
            break
        j = raw.find(b"endstream", i)
        if j < 0:
            break
        body = raw[i + 6:j].lstrip(b" " + bytes([13, 10]))
        pos = j + 9
        stream_count += 1
        if len(body) < 8:
            continue
        data = None
        try:
            data = zlib.decompress(body)
        except Exception:
            try:
                data = zlib.decompress(body, -15)
            except Exception:
                data = body
        if b"Tj" in data or b"TJ" in data:
            t = extract_ops(data)
            if t.strip():
                texts.append(t)

    if not texts:
        return None, ("这个 PDF 抽不出文本（可能是扫描版图片 PDF，共 " +
                      str(stream_count) + " 个流）。请先 OCR 转文字再导入。")
    txt = NL.join(texts)
    txt = re.sub(NL + "{3,}", NL + NL, txt)
    return txt.strip(), None


def extract_ops(data):
    out = []
    pat1 = re.compile(rb"[(](.*?)[)]\s*Tj", re.S)
    for m in pat1.finditer(data):
        out.append(decode_pdf_string(m.group(1)))
    pat2 = re.compile(rb"[(](.*?)[)]\s*TJ", re.S)
    for m in pat2.finditer(data):
        parts = []
        for sm in pat1_inner(m.group(1)):
            parts.append(decode_pdf_string(sm))
        if parts:
            out.append("".join(parts))
    return NL.join(x for x in out if x)


def pat1_inner(inner):
    pat = re.compile(rb"[(](.*?)[)]", re.S)
    return [m.group(1) for m in pat.finditer(inner)]

def decode_pdf_string(b):
    esc = bytes([92])
    reps = [
        (esc + b"n", b" "), (esc + b"r", b" "), (esc + b"t", b" "),
        (esc + lp_(), lp_()), (esc + rp_(), rp_()), (esc + esc, esc),
    ]
    for a, c in reps:
        b = b.replace(a, c)
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return b.decode("latin-1")
        except Exception:
            return ""


def lp_():
    return bytes([40])


def rp_():
    return bytes([41])


def extract(path):
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".docx":
        return read_docx(p)
    if ext == ".pdf":
        return read_pdf(p)
    if ext in (".txt", ".md", ".markdown"):
        for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030", "big5"):
            try:
                return p.read_text(encoding=enc), None
            except UnicodeDecodeError:
                continue
        return None, "无法识别文本编码"
    if ext == ".doc":
        return None, "旧版 .doc 不支持，请另存为 .docx"
    return None, "不支持的格式：" + ext