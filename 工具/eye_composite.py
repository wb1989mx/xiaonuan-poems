# -*- coding: utf-8 -*-
"""
闭眼 patch 回贴：把生成的闭眼图对齐回头区原图，只取眼区像素合成，
输出透明 patch + 眨眼对照预览 + 坐标 JSON。
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
from key_and_preview import sample_bg  # noqa: E402

ROOT = Path(r"D:\Doubao\活学活用\儿童学习平台")
PREVIEW = ROOT / "素材库" / "_预览"
ROLE = ROOT / "素材库" / "共用_角色" / "10_分层"
CREAM = (255, 247, 236, 255)
POSES = ["sit", "stand", "walk"]


# ---------- 基础量 ----------
def bg_dist(arr, bg):
    return np.sqrt(((arr.astype(np.float32) - bg) ** 2).sum(axis=2))


def content_box(im, t=60.0):
    arr = np.asarray(im.convert("RGB")).astype(np.float32)
    bg = sample_bg(arr)
    m = bg_dist(arr, bg) > t
    ys, xs = np.where(m)
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1), m


def eye_rect(im, thr=78.0, debug=None):
    """
    两只眼睛 = 一组连通的暗块，且块内含白色高光（虹膜反光）。
    按面积/宽高比/是否含高光筛候选，再挑左右成对的。
    """
    from scipy import ndimage as ndi

    arr = np.asarray(im.convert("RGB")).astype(np.float32)
    L = arr.mean(axis=2)
    h, w = L.shape
    y0, y1 = int(0.22 * h), int(0.70 * h)
    x0, x1 = int(0.04 * w), int(0.78 * w)
    sub = L[y0:y1, x0:x1]

    lab, n = ndi.label(sub < thr)
    cands = []
    for i, sl in enumerate(ndi.find_objects(lab), start=1):
        if sl is None:
            continue
        m = lab[sl] == i
        area = int(m.sum())
        hh, ww = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if sl[0].start < 4 or sl[1].start < 4:
            continue                      # 贴边的一块不是脸内元素
        if not (700 <= area <= 6000) or hh < 35 or ww > 110:
            continue
        if ww / hh > 1.35:
            continue                      # 眼睛竖着比横着长；鼻子/嘴巴是扁的
        holes = int((ndi.binary_fill_holes(m) & ~m).sum())
        if holes < 15:
            continue                      # 眼里的白色高光会留下孔洞
        bx = (x0 + sl[1].start, y0 + sl[0].start, x0 + sl[1].stop, y0 + sl[0].stop)
        cands.append({"box": bx, "w": ww, "h": hh, "area": area, "holes": holes,
                      "cx": (bx[0] + bx[2]) / 2, "cy": (bx[1] + bx[3]) / 2})
    if debug is not None:
        d = im.copy()
        dr = ImageDraw.Draw(d)
        for c in cands:
            dr.rectangle(c["box"], outline=(0, 255, 120), width=3)
            dr.text((c["box"][0], c["box"][1] - 12),
                    f"{c['area']}/{c['w']}x{c['h']}", fill=(0, 255, 120))
        d.save(debug)
    if len(cands) < 2:
        raise RuntimeError(f"只找到 {len(cands)} 个眼睛候选："
                           f"{[(c['area'], c['w'], c['h']) for c in cands]}")

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
    print("    候选:", [(c["area"], c["w"], c["h"], c["box"][0], c["box"][1]) for c in cands],
          "| 选中:", a["box"], b["box"])
    a, b = best[1], best[2]
    x0b = min(a["box"][0], b["box"][0]); y0b = min(a["box"][1], b["box"][1])
    x1b = max(a["box"][2], b["box"][2]); y1b = max(a["box"][3], b["box"][3])
    ex = int((x1b - x0b) * 0.14)
    ey = int((y1b - y0b) * 0.26)
    rect = (max(0, x0b - ex), max(0, y0b - ey), min(w, x1b + ex), min(h, y1b + ey))
    return tuple(int(v) for v in rect)


# ---------- 对齐 ----------
def align(orig, gen):
    """按内容框把生成图相似变换到原图坐标系。"""
    ob, _ = content_box(orig)
    gb, _ = content_box(gen)
    kx = (gb[2] - gb[0]) / (ob[2] - ob[0])   # 生成图每 1 个原图像素对应多少像素
    ky = (gb[3] - gb[1]) / (ob[3] - ob[1])
    # 输出坐标(x,y) → 生成图坐标 (kx*x + c, ky*y + f)，c/f 让两侧内容框左上角重合
    a, c = kx, gb[0] - ob[0] * kx
    e, f = ky, gb[1] - ob[1] * ky
    out = gen.convert("RGB").transform(orig.size, Image.AFFINE, (a, 0, c, 0, e, f),
                                       resample=Image.BICUBIC)
    return out, (kx, ky)


def match_color(src, dst, box):
    """把 src 在 box 内的像素，均值方差对到 dst 同区域，消除重绘造成的色差。"""
    s = np.asarray(src.crop(box)).astype(np.float32)
    d = np.asarray(dst.crop(box)).astype(np.float32)
    for ch in range(3):
        s[..., ch] = (s[..., ch] - s[..., ch].mean()) * (d[..., ch].std() / (s[..., ch].std() + 1e-6)) \
                     + d[..., ch].mean()
    return Image.fromarray(np.clip(s, 0, 255).astype(np.uint8))


def compose(pose, feather=10):
    orig = Image.open(PREVIEW / f"head_{pose}.png").convert("RGB")
    gen = Image.open(PREVIEW / f"gen_{pose}.png")
    gen, ks = align(orig, gen)
    box = eye_rect(orig, debug=PREVIEW / f"eye_detect_{pose}.png")
    patch = match_color(gen, orig, box)

    # 羽化 mask
    mask = Image.new("L", (box[2] - box[0], box[3] - box[1]), 255)
    ImageDraw.Draw(mask).rectangle([0, 0, mask.width - 1, mask.height - 1], outline=0, width=0)
    mask = mask.filter(ImageFilter.GaussianBlur(feather))
    out = orig.copy()
    out.paste(patch, (box[0], box[1]), mask)

    # 透明 patch：只保留眼区，alpha 用压暗后的羽化 mask
    pa = np.dstack([np.asarray(patch), np.asarray(mask)])
    pimg = Image.fromarray(pa.astype(np.uint8), "RGBA")
    dst_dir = ROLE / pose
    pimg.save(dst_dir / f"eye-close_{pose}.png")

    info = {
        "pose": pose,
        "box": box,
        "align_scale": [round(float(ks[0]), 4), round(float(ks[1]), 4)],
        "patch_size": pimg.size,
        "patch_file": str(dst_dir / f"eye-close_{pose}.png"),
        "head_crop": str(PREVIEW / f"head_{pose}.png"),
    }
    print(f"{pose:5s} 眼区{box} 对齐缩放{info['align_scale']} patch{pimg.size}")
    return orig, out, box, info


def blink_sheet(items, dst, scale=0.5, zoom=2.0):
    """每行一种姿态：睁眼原图 | 闭眼合成 | 眼区放大（睁 / 闭）。"""
    gap, pad = 18, 22
    rows = []
    for orig, closed, box, _ in items:
        half = (int(orig.width * scale), int(orig.height * scale))
        a = orig.resize(half, Image.LANCZOS)
        b = closed.resize(half, Image.LANCZOS)
        zb = (max(0, box[0] - 16), max(0, box[1] - 16),
              min(orig.width, box[2] + 16), min(orig.height, box[3] + 16))
        size = (int((zb[2] - zb[0]) * zoom), int((zb[3] - zb[1]) * zoom))
        z1 = orig.crop(zb).resize(size, Image.LANCZOS)
        z2 = closed.crop(zb).resize(size, Image.LANCZOS)
        rows.append((a, b, z1, z2))

    rh = max(max(r[0].height, r[1].height, r[2].height) for r in rows)
    half_w = max(r[0].width for r in rows)
    zoom_w = max(r[2].width for r in rows)
    total_w = pad * 2 + half_w * 2 + gap * 2 + zoom_w * 2 + gap
    total_h = pad * 2 + rh * len(rows) + gap * (len(rows) - 1)
    canvas = Image.new("RGB", (total_w, total_h), (58, 58, 58))
    y = pad
    for a, b, z1, z2 in rows:
        x = pad
        canvas.paste(a, (x, y + (rh - a.height) // 2)); x += half_w + gap
        canvas.paste(b, (x, y + (rh - b.height) // 2)); x += half_w + gap
        canvas.paste(z1, (x, y + (rh - z1.height) // 2)); x += zoom_w + gap
        canvas.paste(z2, (x, y + (rh - z2.height) // 2))
        y += rh + gap
    canvas.save(dst)
    print("预览 ->", dst)


if __name__ == "__main__":
    items, infos = [], []
    for p in POSES:
        o, c, b, i = compose(p)
        items.append((o, c, b, i))
        infos.append(i)
    blink_sheet(items, PREVIEW / "眨眼_三姿态.png")
    meta = ROOT / "素材库" / "共用_角色" / "10_分层" / "eye_patch.json"
    meta.write_text(json.dumps(infos, ensure_ascii=False, indent=2), encoding="utf-8")
    print("坐标 ->", meta)
