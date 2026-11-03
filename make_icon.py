# 跑团 KP · 本地 COC 7th / DND 5e 桌面跑团工具
# https://github.com/xiangshu2026/rp-kp
#
# 从一张源图生成 kp.png / kp.ico（512px 圆角 + 金色描边，跟软件主题一致）。
# 用法：
#   python make_icon.py 源图路径
# 不给路径时读环境变量 KP_ICON_SRC；都不给就用仓库里的 preview.png。
from PIL import Image, ImageDraw
from pathlib import Path
import os, sys

ROOT = Path(__file__).resolve().parent

src = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('KP_ICON_SRC', str(ROOT / 'preview.png'))
img = Image.open(src).convert("RGBA")
print("原始尺寸:", img.size)

# 居中裁成正方形（保留主体，避免边缘被切）
w, h = img.size
side = min(w, h)
left = (w - side) // 2
# 稍微上移取景，让主体和人群都在
top = max(0, int((h - side) * 0.42))
sq = img.crop((left, top, left + side, top + side))
sq = sq.resize((512, 512), Image.LANCZOS)

# 圆角遮罩
mask = Image.new("L", (512, 512), 0)
d = ImageDraw.Draw(mask)
d.rounded_rectangle([0, 0, 512, 512], radius=92, fill=255)
out = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
out.paste(sq, (0, 0), mask)

# 金色描边，跟软件主题一致
dr = ImageDraw.Draw(out)
dr.rounded_rectangle([3, 3, 508, 508], radius=90, outline=(200, 153, 74, 235), width=7)

out.save(ROOT / "kp.png")
sizes = [(256,256),(128,128),(96,96),(64,64),(48,48),(32,32),(24,24),(16,16)]
out.save(ROOT / "kp.ico", sizes=sizes)
print("图标已生成:", ROOT / "kp.png", ROOT / "kp.ico")
