# -*- coding: utf-8 -*-
"""
闭眼 patch（程序化版）：定位双眼 → 用眼周最近像素填平眼球 → 画闭合眼睑弧线与睫毛。
不产生矩形接缝，像素对齐由构造保证。输出透明 patch + 坐标 JSON + 对照预览。
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi
from scipy.spatial import ConvexHull

ROOT = Path(r"D:\Doubao\活学活用\儿童学习平台")
PREVIEW = ROOT / "素材库" / "_预览"
ROLE = ROOT / "素材库" / "共用_角色" / "10_分层"
POSES = ["sit", "stand", "walk"]


# ---------------------------------------------------------------- 检测
def detect_eyes(im, thr=80.0):
    """返回两只眼睛的 (box, 眼球掩膜)；按'略竖、内部带高光孔洞'筛块再左右配对。"""
    arr = np.asarray(im.convert("RGB")).astype(np.float32)
    L = arr.mean(axis=2)
    h, w = L.shape
    y0, y1 = int(0.22 * h), int(0.70 * h)
    x0, x1 = int(0.04 * w), int(0.78 * w)
    sub = L[y0:y1, x0:x1]
    lab, _ = ndi.label(sub < thr)

    cands = []
    for i, sl in enumerate(ndi.find_objects(lab), start=1):
        if sl is None:
            continue
        core = lab[sl] == i
        hh, ww = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        area = int(core.sum())
        if sl[0].start < 4 or sl[1].start < 4:
            continue
        if not (700 <= area <= 6000) or hh < 35 or ww > 110 or ww / hh > 1.35:
            continue
        if int((ndi.binary_fill_holes(core) & ~core).sum()) < 15:
            continue
        full = np.zeros((h, w), dtype=bool)
        full[y0 + sl[0].start:y0 + sl[0].stop, x0 + sl[1].start:x0 + sl[1].stop] = core
        box = (x0 + sl[1].start, y0 + sl[0].start, x0 + sl[1].stop, y0 + sl[0].stop)
        cands.append({"box": box, "mask": full, "area": area, "w": ww, "h": hh,
                      "cx": (box[0] + box[2]) / 2, "cy": (box[1] + box[3]) / 2})

    best = None
    for i in range(len(cands)):
        for j in range(i + 1, len(cands)):
            a, b = cands[i], cands[j]
            if abs(a["cy"] - b["cy"]) > 0.45 * max(a["h"], b["h"]):
                continue
            if abs(a["cx"] - b["cx"]) < 1.5 * max(a["w"], b["w"]):
                continue
            score = (abs(a["area"] - b["area"]) / max(a["area"], b["area"])
                     + abs(a["h"] - b["h"]) / max(a["h"], b["h"])
                     + abs(a["cy"] - b["cy"]) / max(1, 0.5 * max(a["h"], b["h"])))
            if best is None or score < best[0]:
                best = (score, a, b)
    if best is None:
        raise RuntimeError("没找到成对的眼睛")
    a, b = best[1], best[2]
    return (a, b) if a["cx"] < b["cx"] else (b, a)


# ---------------------------------------------------------------- 绘制
SS = 4  # 超采样倍数


def ink_mask(size, painter):
    """在 SS 倍画布上作画，降采样得到抗锯齿的墨迹 alpha。"""
    cw, ch = size
    m = Image.new("L", (cw * SS, ch * SS), 0)
    d = ImageDraw.Draw(m)
    painter(d, SS, cw, ch)
    return np.asarray(m.resize(size, Image.LANCZOS)).astype(np.float32) / 255.0


def draw_closed_eye(w, h, outward):
    """在 w×h 画布里画一条上拱的眼睑弧线 + 外眼角两三根睫毛。返回 ink alpha。"""
    thick = max(3.0, h * 0.058)
    arc_h = h * 0.24
    x_lo, x_hi = w * 0.10, w * 0.90
    base_y = h * 0.62          # 眼睑线压在眼睛中线偏下，下方不留大片空白
    n = 220

    def stroke(d, S, cw, ch):
        pts = []
        for t in np.linspace(0, 1, n):
            x = x_lo + (x_hi - x_lo) * t
            y = base_y - arc_h * np.sin(np.pi * t)
            pts.append((x * S, y * S))
        # 沿曲线盖圆点，实现可变粗细的平滑笔画
        r = thick * S / 2
        for i, (x, y) in enumerate(pts):
            k = np.sin(np.pi * (i / (n - 1)))
            rr = r * (0.55 + 0.45 * k)          # 中段略粗，两端收细
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=255)
        # 睫毛：外眼角三根
        ex = (x_hi if outward > 0 else x_lo) * S
        ey = (base_y - arc_h * np.sin(np.pi * (0.99 if outward > 0 else 0.01))) * S
        for k, (dx, dy, ln) in enumerate([(0.20, -0.34, 0.16), (0.30, -0.18, 0.14),
                                          (0.10, -0.46, 0.12)]):
            l = ln * h * S
            d.line([ex, ey, ex + dx * outward * l * 2.2, ey + dy * l * 2.4],
                   fill=255, width=max(2, int(thick * S * 0.42)))

    return ink_mask((w, h), stroke)


def membrane_fill(arr, mask):
    """
    按列做上下边界线性插值：眼睛正上是棕色眉弓、正下是桃色脸颊，
    逐列插值天然延续这张脸的明暗梯度，不会像各向同性外推那样被平均成一片浅色。
    """
    h, w = mask.shape
    rows = np.arange(h)[:, None]
    top = np.maximum.accumulate(np.where(~mask, rows, -1), axis=0)
    bot = np.minimum.accumulate(np.where(~mask, rows, h)[::-1], axis=0)[::-1]
    out = arr.copy()
    ys, xs = np.where(mask)
    t = top[ys, xs]
    b = bot[ys, xs]
    t_safe = np.clip(t, 0, h - 1)
    b_safe = np.clip(b, 0, h - 1)
    d_t = np.where(t >= 0, ys - t, 1e9)
    d_b = np.where(b < h, b - ys, 1e9)
    wt = np.where(d_t < 1e9, 1.0 / np.maximum(d_t, 1e-6), 0.0)
    wb = np.where(d_b < 1e9, 1.0 / np.maximum(d_b, 1e-6), 0.0)
    s = wt + wb
    s = np.where(s < 1e-9, 1e-9, s)
    v = (arr[t_safe, xs] * wt[:, None] + arr[b_safe, xs] * wb[:, None]) / s[:, None]
    out[ys, xs] = np.clip(v, 0, 255)
    return out


def grain_std(arr, mask):
    """量出原画颗粒强度：整图减去小半径模糊后的残差标准差。"""
    blurred = np.asarray(Image.fromarray(arr.astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(2.0))).astype(np.float32)
    resid = (arr - blurred)[~mask]
    return float(np.std(resid))


def build_patch(im, eye, ink_rgb, m=6):
    """膜插值填平眼球 + 叠加墨迹，输出 (patch RGBA, 放置坐标)。"""
    arr = np.asarray(im.convert("RGB")).astype(np.float32)
    box = eye["box"]
    core = eye["mask"]
    L = arr.mean(axis=2)
    sat = arr.max(axis=2) - arr.min(axis=2)
    white = (sat < 25) & (L > 205)          # 眼白/高光：接近纯白、低饱和
    win = np.zeros_like(core)
    win[max(0, box[1] - 18):box[3] + 18, max(0, box[0] - 18):box[2] + 18] = True
    # 眼球 = 瞳孔暗块 + 贴着它的白月牙。取两者并集的凸包，一次盖住整只眼，
    # 再外扩 4px 吃掉贴边漏出的一线眼白。
    pts_src = core | (white & win)
    ys, xs = np.where(pts_src)
    pts = np.stack([xs, ys], axis=1).astype(np.float64)
    hull = ConvexHull(pts)
    poly = [tuple(p) for p in pts[hull.vertices]]
    m_img = Image.new("L", (arr.shape[1], arr.shape[0]), 0)
    ImageDraw.Draw(m_img).polygon(poly, fill=255)
    mask = np.asarray(m_img) > 0
    mask = ndi.binary_dilation(mask, iterations=6)

    filled = membrane_fill(arr, mask)
    g = grain_std(arr, mask)
    rng = np.random.default_rng(7)
    noise = rng.normal(0.0, g * 0.75, size=(mask.sum(), 1))
    filled[mask] = np.clip(filled[mask] + noise, 0, 255)

    box = eye["box"]
    w, h = box[2] - box[0], box[3] - box[1]
    outward = -1 if eye["cx"] < (im.width * 0.35) else 1
    ink = draw_closed_eye(w, h, outward)

    canvas = filled[box[1]:box[3], box[0]:box[2]].copy()
    sub_mask = mask[box[1]:box[3], box[0]:box[2]]
    k = ink > 0.02
    canvas[k] = canvas[k] * (1 - ink[k])[:, None] + np.array(ink_rgb, dtype=np.float32) * ink[k][:, None]

    alpha = np.maximum(sub_mask.astype(np.float32), ink)
    alpha_img = Image.fromarray((alpha * 255).astype(np.uint8), "L").filter(
        ImageFilter.GaussianBlur(1.2))
    alpha = np.asarray(alpha_img).astype(np.float32) / 255.0

    pw, ph = w + m * 2, h + m * 2
    pad_rgb = np.tile(np.array(ink_rgb, dtype=np.float32), (ph, pw, 1))
    pad_a = np.zeros((ph, pw), dtype=np.float32)
    pad_rgb[m:m + h, m:m + w] = canvas
    pad_a[m:m + h, m:m + w] = alpha
    patch = Image.fromarray(np.dstack([pad_rgb, pad_a * 255]).astype(np.uint8), "RGBA")
    return patch, (box[0] - m, box[1] - m)


def compose(pose):
    im = Image.open(PREVIEW / f"head_{pose}.png").convert("RGB")
    arr = np.asarray(im).astype(np.float32)
    eyes = detect_eyes(im)

    # 墨色取眼珠最暗的 15% 的均值，保证与原画同一色系
    dark = np.concatenate([arr[e["mask"]].mean(axis=1) for e in eyes])
    thr_c = np.percentile(dark, 15)
    ink_rgb = tuple(float(v) for v in np.mean(
        [arr[e["mask"]][arr[e["mask"]].mean(axis=1) <= thr_c].mean(axis=0) for e in eyes], axis=0))
    ink_rgb = tuple(int(v) for v in ink_rgb)

    out = im.copy()
    boxes = []
    dst_dir = ROLE / pose
    dst_dir.mkdir(parents=True, exist_ok=True)
    for k, e in enumerate(eyes, start=1):
        patch, pos = build_patch(im, e, ink_rgb)
        out.paste(patch, pos, patch)
        pf = dst_dir / f"eye-close_{pose}-{k}.png"
        patch.save(pf)
        boxes.append({"patch": [pos[0], pos[1], pos[0] + patch.width, pos[1] + patch.height],
                      "eye": list(e["box"]), "file": str(pf), "size": list(patch.size)})
    return im, out, eyes, ink_rgb, boxes


def sheet(rows, dst, scale=0.5, zoom=2.0):
    gap, pad = 18, 22
    cells = []
    for orig, closed, eyes, _ in rows:
        x0 = min(e["box"][0] for e in eyes) - 18
        y0 = min(e["box"][1] for e in eyes) - 18
        x1 = max(e["box"][2] for e in eyes) + 18
        y1 = max(e["box"][3] for e in eyes) + 18
        zb = (max(0, x0), max(0, y0), min(orig.width, x1), min(orig.height, y1))
        size = (int((zb[2] - zb[0]) * zoom), int((zb[3] - zb[1]) * zoom))
        cells.append([orig.resize((int(orig.width * scale), int(orig.height * scale)), Image.LANCZOS),
                      closed.resize((int(orig.width * scale), int(orig.height * scale)), Image.LANCZOS),
                      orig.crop(zb).resize(size, Image.LANCZOS),
                      closed.crop(zb).resize(size, Image.LANCZOS)])
    rh = max(max(c[0].height, c[1].height, c[2].height) for c in cells)
    hw = max(c[0].width for c in cells)
    zw = max(c[2].width for c in cells)
    W = pad * 2 + hw * 2 + gap * 2 + zw * 2 + gap
    H = pad * 2 + rh * len(cells) + gap * (len(cells) - 1)
    canvas = Image.new("RGB", (W, H), (58, 58, 58))
    y = pad
    for c in cells:
        x = pad
        for img, wcell in ((c[0], hw), (c[1], hw), (c[2], zw), (c[3], zw)):
            canvas.paste(img, (x, y + (rh - img.height) // 2))
            x += wcell + gap
        y += rh + gap
    canvas.save(dst)
    print("预览 ->", dst)


if __name__ == "__main__":
    rows, meta = [], []
    for p in POSES:
        orig, closed, eyes, ink, boxes = compose(p)
        rows.append((orig, closed, eyes, p))
        meta.append({"pose": p, "ink_rgb": ink, "patches": boxes,
                     "head_crop": str(PREVIEW / f"head_{p}.png")})
        print(f"{p:5s} 眼区 {[b['eye'] for b in boxes]} 墨色 {ink} "
              f"patch {[b['size'] for b in boxes]}")
    sheet(rows, PREVIEW / "眨眼_程序绘制.png")
    (ROLE / "eye_patch.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("坐标 ->", ROLE / "eye_patch.json")
