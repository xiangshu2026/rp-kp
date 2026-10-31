# 跑团 KP · 本地 COC 7th / DND 5e 桌面跑团工具
# https://github.com/xiangshu2026/rp-kp
from PIL import Image, ImageDraw, ImageOps
import sys
src = r"C:/Users/YourName/.dsh/attachments/v1/objects/e5/e5ca58746c90cd14b162bd0246205f53dd6c242849f1d1319fd6e9d289449d52"
img = Image.open(src).convert("RGBA")
print("原始尺寸:", img.size)

# 居中裁成正方形（这张是竖构图，保留十字架与人群）
w, h = img.size
side = min(w, h)
left = (w - side) // 2
# 稍微上移取景，让十字架和人群都在
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

out.save(r"E:\deepseek工作区\rp-kp-app\kp.png")
sizes = [(256,256),(128,128),(96,96),(64,64),(48,48),(32,32),(24,24),(16,16)]
out.save(r"E:\deepseek工作区\rp-kp-app\kp.ico", sizes=sizes)
print("图标已生成")