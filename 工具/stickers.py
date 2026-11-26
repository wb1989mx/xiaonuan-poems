# -*- coding: utf-8 -*-
"""贴纸后处理：把生成的方形奶油底徽章图，统一成正圆、居中、透明底、512×512。
步骤：下载 → 找徽章圆（非奶油的像素包围盒）→ 以圆心重裁 → 4x 超采样圆遮罩 → 缩到 512。
"""
import os, io, urllib.request
import numpy as np
from PIL import Image, ImageDraw

ROOT = r"D:\Doubao\活学活用\儿童学习平台\素材库\诗词"
OUT_PREVIEW = r"D:\Doubao\活学活用\儿童学习平台\素材库\_预览"
SIDE = 512          # 出口尺寸
PAD = 0.06          # 圆外留白占整幅比例
SS = 4              # 遮罩超采样倍数
THRESH = 15         # 与奶油底的最小通道差

ITEMS = [
    ("01_咏鹅", "01", "https://aka.doubaocdn.com/s/fVxtj6sCzD"),
    ("02_静夜思", "02", "https://aka.doubaocdn.com/s/N9S26l1te6"),
    ("03_春晓", "03", "https://aka.doubaocdn.com/s/8qLD6DZNfT"),
    ("04_池上", "04", "https://aka.doubaocdn.com/s/DMbSUU54X3"),
    ("05_小池", "05", "https://aka.doubaocdn.com/s/1K7yg1U8w0"),
    ("06_村居", "06", "https://aka.doubaocdn.com/s/H5Uxrrjn67"),
    ("07_咏柳", "07", "https://aka.doubaocdn.com/s/1NzUAxj7kd"),
    ("08_登鹳雀楼", "08", "https://aka.doubaocdn.com/s/k3BXNyFtZW"),
    ("09_望庐山瀑布", "09", "https://aka.doubaocdn.com/s/MYwfUyAZe3"),
    ("10_江雪", "10", "https://aka.doubaocdn.com/s/zI2MEFDdhh"),
]


def load(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=60).read())).convert("RGB")


def paper_color(im):
    a = np.asarray(im).astype(np.float32)
    h, w, _ = a.shape
    k = 24
    patches = [a[:k, :k], a[:k, -k:], a[-k:, :k], a[-k:, -k:]]
    return np.median(np.concatenate([p.reshape(-1, 3) for p in patches]), axis=0)


def circle_bbox(im):
    a = np.asarray(im).astype(np.float32)
    bg = paper_color(im)
    d = np.abs(a - bg).max(axis=2)
    m = d > THRESH
    ys, xs = np.where(m)
    if len(xs) == 0:
        return None
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = max(x1 - x0, y1 - y0) / 2
    return cx, cy, r


def build(im, out_path, name):
    box = circle_bbox(im)
    if box is None:
        raise RuntimeError(f"{name} 找不到徽章圆")
    cx, cy, r = box
    side = int(round(2 * r * (1 + PAD)))
    # 以圆心为中心裁正方形（越界处补奶油底，理论上不会越界）
    half = side / 2
    crop = Image.new("RGB", (side, side), tuple(int(v) for v in paper_color(im)))
    crop.paste(im, (int(round(half - cx)), int(round(half - cy))))
    crop = crop.resize((SIDE * SS, SIDE * SS), Image.LANCZOS)

    # 圆遮罩（在超采样尺度上画，再缩回来做抗锯齿）
    mask = Image.new("L", (SIDE * SS, SIDE * SS), 0)
    d = ImageDraw.Draw(mask)
    rr = SIDE * SS / 2 * (1 / (1 + PAD)) * SS / SS  # 圆半径占整幅 = 1/(1+PAD)
    rr = SIDE * SS / 2 / (1 + PAD) * (1 + PAD) / 1  # 简化：直接用 2r/side 比例
    rr = (SIDE * SS / 2) * (2 * r / side)
    d.ellipse([SIDE * SS / 2 - rr, SIDE * SS / 2 - rr, SIDE * SS / 2 + rr, SIDE * SS / 2 + rr], fill=255)
    mask = mask.resize((SIDE, SIDE), Image.LANCZOS)
    crop = crop.resize((SIDE, SIDE), Image.LANCZOS)

    out = crop.convert("RGBA")
    out.putalpha(mask)
    out.save(out_path, optimize=True)
    return out_path, (cx, cy, r, side)


def main():
    made = []
    for folder, num, url in ITEMS:
        d = os.path.join(ROOT, folder, "贴纸")
        os.makedirs(d, exist_ok=True)
        im = load(url)
        p = os.path.join(d, f"{num}-sticker.png")
        build(im, p, num)
        out = Image.open(p)
        made.append(out)
        print(f"{num}  {im.size} -> {out.size}  {os.path.getsize(p)/1024:.0f}KB  {p}")

    # 十枚对照图
    cell, pad = 300, 16
    sh = Image.new("RGB", (cell * 5 + pad * 6, cell * 2 + pad * 3), (255, 247, 236))
    for i, out in enumerate(made):
        r_, c_ = divmod(i, 5)
        t = out.resize((cell, cell), Image.LANCZOS)
        sh.paste(t, (pad + c_ * (cell + pad), pad + r_ * (cell + pad)), t)
    psh = os.path.join(OUT_PREVIEW, "贴纸_十枚.png")
    sh.save(psh)
    print("sheet", psh, sh.size)


if __name__ == "__main__":
    main()
