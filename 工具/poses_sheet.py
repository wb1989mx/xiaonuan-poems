# -*- coding: utf-8 -*-
"""
三姿态抠图 + 按"头宽"归一 + 三姿态对照表。
为什么要归一：三张图各自生成，模型给的头身比不一样，并排一看就是三个不同的小鹿。
以头部（含双耳）宽度为基准缩放，是唯一与姿态无关、又能反映角色体量的量。
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from key_and_preview import key_magenta, CREAM

ROOT = Path(r"D:\Doubao\活学活用\儿童学习平台")
BASE = ROOT / "素材库" / "共用_角色" / "10_分层"
PREVIEW = ROOT / "素材库" / "_预览"

POSES = ["sit", "stand", "walk"]
TARGET_HEAD_W = 260
TOP_RATIO = 0.42


def head_width(im: Image.Image) -> int:
    a = np.array(im)[:, :, 3] > 40
    rows = a[:int(im.height * TOP_RATIO)]
    return int(rows.sum(axis=1).max())


def load_keyed(pose: str):
    src = BASE / pose / f"full-{pose}.png"
    if not src.exists():
        return None, f"缺少 {src.name}"
    dst = BASE / pose / f"full-{pose}_alpha.png"
    info = key_magenta(src, dst)
    return Image.open(dst).convert("RGBA"), info


if __name__ == "__main__":
    PREVIEW.mkdir(parents=True, exist_ok=True)
    items, notes = [], []
    for p in POSES:
        img, info = load_keyed(p)
        if img is None:
            notes.append(info)
            continue
        hw = head_width(img)
        k = TARGET_HEAD_W / hw
        new = img.resize((round(img.width * k), round(img.height * k)), Image.LANCZOS)
        items.append((p, new, hw, k))
        notes.append(f"{p}: 原 {info['size']} 头宽{hw}px 缩放{k:.2f} -> {new.width}x{new.height}")

    if not items:
        print("\n".join(notes))
        sys.exit(1)

    gap, margin = 30, 30
    max_h = max(i.height for _, i, _, _ in items)
    total_w = sum(i.width for _, i, _, _ in items) + gap * (len(items) - 1) + margin * 2
    canvas = Image.new("RGBA", (total_w, max_h + margin * 2), CREAM)

    x = margin
    for _, im, _, _ in items:
        canvas.alpha_composite(im, (x, margin + max_h - im.height))
        x += im.width + gap

    if canvas.width > 1200:
        canvas = canvas.resize((1200, round(canvas.height * 1200 / canvas.width)), Image.LANCZOS)
    out = PREVIEW / "三姿态归一.png"
    canvas.convert("RGB").save(out)
    print("\n".join(notes))
    print(f"对照表：{out}")
