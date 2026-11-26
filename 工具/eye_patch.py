# -*- coding: utf-8 -*-
"""
角色分层收尾：头区裁切（供闭眼编辑）、闭眼结果对齐回贴、验证预览。
依赖：key_and_preview.py 的 sample_bg / key_magenta
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from key_and_preview import sample_bg, key_magenta  # noqa: E402

ROOT = Path(r"D:\Doubao\活学活用\儿童学习平台")
LIB = ROOT / "素材库"
ROLE = LIB / "共用_角色" / "10_分层"
PREVIEW = LIB / "_预览"
CREAM = (255, 247, 236, 255)
POSES = ["sit", "stand", "walk"]


def content_bbox(path: Path, t=60.0, pad=0):
    im = Image.open(path).convert("RGB")
    arr = np.asarray(im).astype(np.float32)
    bg = sample_bg(arr)
    dist = np.sqrt(((arr - bg) ** 2).sum(axis=2))
    mask = dist > t
    ys, xs = np.where(mask)
    x0, x1 = int(xs.min()) - pad, int(xs.max()) + pad
    y0, y1 = int(ys.min()) - pad, int(ys.max()) + pad
    return (max(0, x0), max(0, y0), min(im.width, x1 + 1), min(im.height, y1 + 1))


def crop_heads(ratio=0.62, margin=0.10):
    """每种姿态取内容框上部一段作为头区，左右各留 margin 余量。"""
    PREVIEW.mkdir(parents=True, exist_ok=True)
    out = []
    for p in POSES:
        src = ROLE / p / f"full-{p}.png"
        box = content_bbox(src)
        w, h = box[2] - box[0], box[3] - box[1]
        hh = int(h * ratio)
        cx = (box[0] + box[2]) // 2
        half = int(w * (0.5 + margin))
        crop = (max(0, cx - half), max(0, box[1] - int(h * 0.02)),
                min(Image.open(src).width, cx + half), box[1] + hh)
        im = Image.open(src).convert("RGB").crop(crop)
        dst = PREVIEW / f"head_{p}.png"
        im.save(dst)
        out.append({"pose": p, "src": src, "box": crop, "size": im.size, "file": dst})
        print(f"{p:5s} 内容框{box}  头区{crop}  {im.size}")
    return out


def sheet(items, dst, scale=1.0, gap=20):
    ims = [Image.open(i["file"]).convert("RGB") for i in items]
    if scale != 1.0:
        ims = [i.resize((int(i.width * scale), int(i.height * scale)), Image.LANCZOS) for i in ims]
    h = max(i.height for i in ims)
    w = sum(i.width for i in ims) + gap * (len(ims) + 1)
    canvas = Image.new("RGB", (w, h + gap * 2), (60, 60, 60))
    x = gap
    for i in ims:
        canvas.paste(i, (x, gap + (h - i.height) // 2))
        x += i.width + gap
    canvas.save(dst)
    print(f"预览 -> {dst}")


if __name__ == "__main__":
    items = crop_heads()
    sheet(items, PREVIEW / "head_三姿态.png")
    for i in items:
        print(f"  {i['pose']}: {i['src']}")
