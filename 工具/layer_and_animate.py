# -*- coding: utf-8 -*-
"""
动效方案：整鹿单层 + 呼吸缩放 + 整体轻摆。
不从颈部切分——横切线必然穿过书箩，切出来是两截。
"""
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from key_and_preview import CREAM

ROOT = Path(r"D:\Doubao\活学活用\儿童学习平台")
SIT = ROOT / "素材库" / "共用_角色" / "10_分层" / "sit"
PREVIEW = ROOT / "素材库" / "_预览"

BREATH = 1.016
SWAY = -1.8


def scale_about(img: Image.Image, factor: float, pivot):
    px, py = pivot
    a = 1.0 / factor
    return img.transform(
        img.size, Image.AFFINE,
        (a, 0, px - px * a, 0, a, py - py * a),
        resample=Image.BICUBIC,
    )


def rotate_about(img: Image.Image, deg: float, pivot):
    px, py = pivot
    big = Image.new("RGBA", (img.width * 2, img.height * 2), (0, 0, 0, 0))
    big.alpha_composite(img, (0, 0))
    rot = big.rotate(deg, resample=Image.BICUBIC, center=(px, py))
    return rot.crop((0, 0, img.width, img.height))


def render(deer, breath=1.0, sway=0.0, pad=28):
    pivot = (deer.width / 2, deer.height)
    out = scale_about(deer, breath, pivot)
    if sway:
        out = rotate_about(out, sway, pivot)
    canvas = Image.new("RGBA", (deer.width + pad * 2, deer.height + pad * 2), CREAM)
    canvas.alpha_composite(out, (pad, pad))
    return canvas.convert("RGB")


if __name__ == "__main__":
    keyed = SIT / "full-sit_alpha.png"
    if not keyed.exists():
        print(f"缺少 {keyed}，请先运行 poses_sheet.py")
        sys.exit(1)

    deer = Image.open(keyed).convert("RGBA")
    f0 = render(deer, 1.0, 0.0)
    f1 = render(deer, BREATH, SWAY)

    gap = 20
    pv = Image.new("RGB", (f0.width * 2 + gap, f0.height), CREAM[:3])
    pv.paste(f0, (0, 0))
    pv.paste(f1, (f0.width + gap, 0))
    if pv.width > 1200:
        pv = pv.resize((1200, round(pv.height * 1200 / pv.width)), Image.LANCZOS)
    out = PREVIEW / "动效_整鹿两帧.png"
    pv.save(out)
    print(f"两帧预览：{out}")
