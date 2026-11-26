# -*- coding: utf-8 -*-
"""九类环境层：程序绘制透明 PNG，横向/纵向可无缝循环。
每类两张（不同随机种子，形成相位差与密度差）。
设计原则：叠加物必须"在浅色天空上不发灰、在深色山水上不发白"，
所以每类都是双色结构——亮面近白 + 一层很淡的暖灰/暖赭底边。
"""
import os, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = r"D:\Doubao\活学活用\儿童学习平台\素材库\共用_环境"


def new(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def soft_ellipse(w, h, color, alpha, cx, cy, rx, ry, power=2.0, blur=0):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
    a = np.clip(1.0 - d, 0, 1) ** power * alpha
    img = np.zeros((h, w, 4), np.uint8)
    img[..., 0], img[..., 1], img[..., 2] = color
    img[..., 3] = np.clip(a, 0, 255)
    p = Image.fromarray(img, "RGBA")
    if blur:
        p = p.filter(ImageFilter.GaussianBlur(blur))
    return p


def draw_wrapped(size, item_fn, n, seed):
    """每个元素画完就按九宫格补贴，保证跨边界连续。"""
    w, h = size
    base = new(w, h)
    rnd = random.Random(seed)
    for _ in range(n):
        layer, (x, y) = item_fn((w, h), rnd)
        lw, lh = layer.size
        for dx in (-w, 0, w):
            for dy in (-h, 0, h):
                ox, oy = x + dx, y + dy
                if ox >= w or oy >= h or ox + lw <= 0 or oy + lh <= 0:
                    continue
                base.alpha_composite(layer, (ox, oy),
                                     (max(0, -ox), max(0, -oy), min(lw, w - ox), min(lh, h - oy)))
    return base


# ---------- 01 云 ----------
def make_cloud(seed, w=900, h=320, clouds=3):
    """先做一朵云的剪影（一个扁平底 + 两三个圆顶），再上近白色，
    底部叠一层很淡的暖赭灰，让它有体积又不发脏。"""
    def one(rnd):
        r = rnd.uniform(38, 56)
        bw = int(r * rnd.uniform(4.4, 5.6))
        bh = int(r * 2.9)
        SS = 3
        m = Image.new("L", (bw * SS, bh * SS), 0)
        d = ImageDraw.Draw(m)
        cy = bh * SS * 0.70
        # 扁平底，横向收窄，避免"胶囊"感
        d.ellipse([bw * SS * 0.15, cy - r * SS * 0.46, bw * SS * 0.85, cy + r * SS * 0.60], fill=255)
        # 顶上一串大小不等的圆包
        nb = rnd.randint(3, 4)
        for k in range(nb):
            frac = 0.24 + 0.52 * (k / max(1, nb - 1))
            cx0 = bw * SS * frac + rnd.uniform(-7, 7) * SS
            rr = r * SS * rnd.uniform(0.62, 1.10)
            yo = rnd.uniform(-0.30, 0.06) * rr
            d.ellipse([cx0 - rr * 0.92, cy - yo - rr * 1.05, cx0 + rr * 0.92, cy - yo + rr * 0.52], fill=255)
        m = m.resize((bw, bh), Image.LANCZOS)
        a = np.asarray(m).astype(np.float32) / 255.0
        a = a ** 0.85
        yy = np.mgrid[0:bh, 0:bw][0].astype(np.float32) / bh
        tint = np.clip((yy - 0.58) / 0.42, 0, 1) ** 2 * 0.62
        rgb = np.stack([
            255 - tint * (255 - 236),
            255 - tint * (255 - 216),
            251 - tint * (251 - 198)], axis=2)
        img = np.dstack([rgb, a * 232]).astype(np.uint8)
        p = Image.fromarray(img, "RGBA").filter(ImageFilter.GaussianBlur(3.5))
        return p

    def item(size, rnd):
        p = one(rnd)
        return p, (int(rnd.uniform(-p.width * 0.25, w - p.width * 0.75)),
                   int(rnd.uniform(h * 0.10, h * 0.55)))
    return draw_wrapped((w, h), item, clouds, seed)


# ---------- 02 水面波光 ----------
def make_ripple(seed, n=140, w=900, h=200):
    def item(size, rnd):
        lw = rnd.randint(28, 92)
        lh = max(3, int(lw * rnd.uniform(0.07, 0.13)))
        col = (255, 253, 244) if rnd.random() < 0.75 else (196, 226, 228)
        al = rnd.randint(120, 215)
        p = soft_ellipse(lw + 6, lh + 6, col, al, (lw + 6) / 2, (lh + 6) / 2,
                         lw / 2, lh / 2, 1.3, 1.4)
        return p, (rnd.randint(0, w), rnd.randint(0, h))
    return draw_wrapped((w, h), item, n, seed)


# ---------- 03 树影与光斑 ----------
def make_shadow(seed, w=900, h=520):
    def item(size, rnd):
        if rnd.random() < 0.6:
            rx, ry = rnd.uniform(34, 78), rnd.uniform(22, 50)
            col, al = (255, 241, 202), rnd.randint(45, 90)
        else:
            rx, ry = rnd.uniform(40, 92), rnd.uniform(26, 56)
            col, al = (98, 118, 78), rnd.randint(28, 52)
        bw, bh = int(rx * 2.4), int(ry * 2.4)
        p = soft_ellipse(bw, bh, col, al, bw / 2, bh / 2, rx, ry, 1.4, 11)
        return p, (rnd.randint(0, w) - bw // 2, rnd.randint(0, h) - bh // 2)
    return draw_wrapped((w, h), item, 44, seed)


# ---------- 04 落叶 ----------
def make_leaf(seed, n=16, w=900, h=640):
    cols = [(143, 181, 115), (246, 169, 107), (181, 113, 74), (255, 205, 138)]

    def item(size, rnd):
        L = rnd.randint(34, 58)
        W = L * 2
        p = Image.new("RGBA", (W, W), (0, 0, 0, 0))
        d = ImageDraw.Draw(p)
        col = rnd.choice(cols)
        d.ellipse([W * 0.26, W * 0.38, W * 0.74, W * 0.62], fill=col + (255,))
        d.line([W / 2, W * 0.50, W / 2, W * 0.82], fill=(122, 96, 62, 220), width=2)
        p = p.rotate(rnd.randint(0, 359), resample=Image.BICUBIC)
        p = p.filter(ImageFilter.GaussianBlur(0.5))
        return p, (rnd.randint(0, w), rnd.randint(0, h))
    return draw_wrapped((w, h), item, n, seed)


# ---------- 05 灯焰：模型生成透明底，见 00_规范 §5.1，本脚本不画 ----------


# ---------- 06 细雨 ----------
def make_rain(seed, n=130, w=640, h=640):
    def item(size, rnd):
        ln = rnd.randint(34, 72)
        skew = int(ln * 0.16)
        p = Image.new("RGBA", (skew + 5, ln + 5), (0, 0, 0, 0))
        ImageDraw.Draw(p).line([1, 1, 1 + skew, ln], fill=(208, 226, 226, rnd.randint(80, 150)), width=1)
        return p.filter(ImageFilter.GaussianBlur(0.4)), (rnd.randint(0, w), rnd.randint(0, h))
    return draw_wrapped((w, h), item, n, seed)


# ---------- 07 落雪 ----------
def make_snow(seed, n=90, w=640, h=640):
    """每片雪：一层极淡暖灰底影 + 近白亮面，让它在浅色天空上也看得见。"""
    def item(size, rnd):
        r = rnd.choice([2, 3, 3, 4, 5, 6])
        s = r * 2 + 10
        p = new(s, s)
        p.alpha_composite(soft_ellipse(s, s, (206, 202, 194), rnd.randint(60, 100),
                                       s / 2, s / 2 + 1.5, r * 1.15, r * 1.15, 1.2, 1.2))
        p.alpha_composite(soft_ellipse(s, s, (255, 255, 253), rnd.randint(200, 250),
                                       s / 2, s / 2, r, r, 1.25, 0.7))
        return p, (rnd.randint(0, w), rnd.randint(0, h))
    return draw_wrapped((w, h), item, n, seed)


# ---------- 08 鸟群 ----------
def make_bird(seed, n=7, w=520, h=320):
    """远景鸟：一笔两翼的浅 V，中间略沉。画到 1024 画布上是 20–30px 的小剪影。"""
    def item(size, rnd):
        s = rnd.randint(18, 30)
        span = s * 2
        dep = s * 0.42
        p = Image.new("RGBA", (int(span) + 8, int(dep) + 12), (0, 0, 0, 0))
        col = (58, 46, 38, rnd.randint(150, 195))
        dr = ImageDraw.Draw(p)
        n_pts = 24
        pts = []
        for i in range(n_pts + 1):
            t = i / n_pts
            u = 2 * t - 1
            pts.append((4 + span * t, 4 + dep * (1 - u * u)))
        dr.line(pts, fill=col, width=max(2, int(s * 0.11)), joint="curve")
        return p.filter(ImageFilter.GaussianBlur(0.4)), (rnd.randint(0, w), rnd.randint(0, h))
    return draw_wrapped((w, h), item, n, seed)


# ---------- 09 雾 ----------
def make_mist(seed, w=900, h=300, bands=5):
    base = new(w, h)
    rnd = random.Random(seed)
    for _ in range(bands):
        bh = rnd.randint(80, 150)
        ccy = rnd.randint(int(h * 0.25), int(h * 0.85))
        yy, xx = np.mgrid[0:bh, 0:w].astype(np.float32)
        prof_y = np.clip(1 - np.abs((yy - bh / 2) / (bh / 2)) ** 1.5, 0, 1)
        prof_x = np.clip(np.sin(np.linspace(0, math.pi * rnd.randint(2, 3), w) + rnd.random() * 6), 0, 1) ** 0.9
        a = (prof_y * prof_x[None, :]) * rnd.randint(55, 95)
        img = np.zeros((bh, w, 4), np.uint8)
        img[..., 0], img[..., 1], img[..., 2] = 255, 250, 240
        img[..., 3] = np.clip(a, 0, 255)
        p = Image.fromarray(img, "RGBA").filter(ImageFilter.GaussianBlur(10))
        y = int(np.clip(ccy - bh / 2, 0, h - bh))
        base.alpha_composite(p, (0, y))
    return base


CLASSES = {
    "01_云飘": make_cloud,
    "02_水面波光": make_ripple,
    "03_树影光斑": make_shadow,
    "04_落叶": make_leaf,
    "06_细雨": make_rain,
    "07_落雪": make_snow,
    "08_鸟群": make_bird,
    "09_雾起": make_mist,
}


def main():
    report = []
    for name, fn in CLASSES.items():
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        for k in (1, 2):
            im = fn(seed=k * 7 + 3)
            p = os.path.join(d, f"{name[:2]}-{k}.png")
            im.save(p, optimize=True)
            report.append((name, k, im.size, os.path.getsize(p) / 1024))
    for r in report:
        print(f"{r[0]:12s} v{r[1]}  {r[2]}  {r[3]:6.0f}KB")


if __name__ == "__main__":
    main()
