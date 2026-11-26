# -*- coding: utf-8 -*-
"""
真机尺寸验收：把整鹿缩到实际呈现高度（约 380px）贴在纸底上，
睁眼 / 闭眼并排，检查眨眼在真实尺寸下是否露馅。
"""
from pathlib import Path

from PIL import Image, ImageDraw

PREVIEW = Path(r"D:\Doubao\活学活用\儿童学习平台\素材库\_预览")
CREAM = (255, 247, 236)
TARGET_H = 380          # 1024×768 画布上角色的大致高度


def build(pose, closed, out_path):
    """占位，保留接口一致性；实际由 __main__ 内联完成。"""
    raise NotImplementedError


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from eye_patch_draw import detect_eyes, build_patch

    poses = ["sit", "stand", "walk"]
    cols = []
    for p in poses:
        im = Image.open(PREVIEW / f"head_{p}.png").convert("RGB")
        eyes = detect_eyes(im)
        # 墨色沿用主脚本口径
        import numpy as np
        arr = np.asarray(im).astype(np.float32)
        dark = np.concatenate([arr[e["mask"]].mean(axis=1) for e in eyes])
        t = np.percentile(dark, 15)
        ink = tuple(int(v) for v in np.mean(
            [arr[e["mask"]][arr[e["mask"]].mean(axis=1) <= t].mean(axis=0) for e in eyes], axis=0))
        closed = im.copy()
        for e in eyes:
            patch, pos = build_patch(im, e, ink)
            closed.paste(patch, pos, patch)
        scale = TARGET_H / im.height
        size = (int(im.width * scale), TARGET_H)
        cols.append((im.resize(size, Image.LANCZOS), closed.resize(size, Image.LANCZOS)))

    gap, pad = 26, 30
    n = len(cols) * 2
    W = pad * 2 + sum(c[0].width for c in cols) * 2 + gap * (n - 1)
    H = pad * 2 + TARGET_H + 24
    canvas = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(canvas)
    x = pad
    for a, b in cols:
        canvas.paste(a, (x, pad))
        canvas.paste(b, (x + a.width + gap, pad))
        x += a.width + gap + b.width + gap
    out = PREVIEW / "眨眼_真机尺寸.png"
    canvas.save(out)
    print("真机尺寸预览 ->", out)
