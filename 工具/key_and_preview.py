# -*- coding: utf-8 -*-
"""
素材后处理：纯色背景抠透明、裁边、WebP 压缩、合成预览。
依赖：Pillow、numpy
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(r"D:\Doubao\活学活用\儿童学习平台")
LIB = ROOT / "素材库"
PREVIEW = LIB / "_预览"
CREAM = (255, 247, 236, 255)


def sample_bg(arr: np.ndarray, k=24) -> np.ndarray:
    """取四角小块的逐通道中位数作为背景色。生图给的品红每张都不同，必须每次取样。"""
    corners = np.concatenate([
        arr[:k, :k].reshape(-1, 3), arr[:k, -k:].reshape(-1, 3),
        arr[-k:, :k].reshape(-1, 3), arr[-k:, -k:].reshape(-1, 3),
    ])
    return np.median(corners, axis=0)


def key_magenta(src: Path, dst: Path, t_lo=18.0, t_hi=68.0) -> dict:
    """
    把纯色背景扣成透明。距离小于 t_lo 判为背景（全透明），大于 t_hi 判为实体，中间羽化。
    """
    im = Image.open(src).convert("RGB")
    arr = np.asarray(im).astype(np.float32)
    bg = sample_bg(arr)

    dist = np.sqrt(((arr - bg) ** 2).sum(axis=2))
    alpha = np.clip((dist - t_lo) / (t_hi - t_lo), 0.0, 1.0)

    # 羽化处去掉背景色残留
    rgb = arr.copy()
    semi = (alpha > 0.05) & (alpha < 0.95)
    if semi.any():
        w = (1.0 - alpha[semi])[:, None] * 0.6
        rgb[semi] = rgb[semi] * (1 - w) + bg * w

    rgba = np.dstack([rgb, alpha * 255.0]).astype(np.uint8)
    out = Image.fromarray(rgba, "RGBA")

    bbox = out.getbbox()
    if bbox:
        out = out.crop(bbox)

    out.save(dst)
    return {
        "file": dst.name,
        "size": f"{out.width}x{out.height}",
        "kb": round(dst.stat().st_size / 1024, 1),
        "semi_edge_px": int(((alpha > 0.05) & (alpha < 0.95)).sum()),
    }


def to_webp(src: Path, dst: Path, max_w=1440, quality=82) -> dict:
    im = Image.open(src).convert("RGB")
    if im.width > max_w:
        h = round(im.height * max_w / im.width)
        im = im.resize((max_w, h), Image.LANCZOS)
    im.save(dst, "WEBP", quality=quality, method=6)
    return {
        "file": dst.name,
        "size": f"{im.width}x{im.height}",
        "kb": round(dst.stat().st_size / 1024, 1),
        "src_kb": round(src.stat().st_size / 1024, 1),
    }


def make_preview(parts, dst: Path, gap=24, margin=32):
    ims = [Image.open(p).convert("RGBA") for p in parts]
    h = max(i.height for i in ims)
    w = sum(i.width for i in ims) + gap * (len(ims) - 1) + margin * 2
    canvas = Image.new("RGBA", (w, h + margin * 2), CREAM)
    x = margin
    for i in ims:
        canvas.alpha_composite(i, (x, margin + (h - i.height) // 2))
        x += i.width + gap
    canvas.convert("RGB").save(dst, "PNG")
    return dst


def compress_scenes():
    """把单首诗的场景图压成 WebP，输出到同目录 webp/ 下。"""
    scene_dir = LIB / "诗词" / "02_静夜思" / "场景"
    out_dir = scene_dir / "webp"
    out_dir.mkdir(exist_ok=True)
    total_before = total_after = 0
    for src in sorted(scene_dir.glob("02-s*.png")):
        info = to_webp(src, out_dir / (src.stem + ".webp"))
        total_before += info["src_kb"]
        total_after += info["kb"]
        print(f"  {info['file']}  {info['size']}  {info['src_kb']}KB -> {info['kb']}KB")
    if total_before:
        print(f"  合计 {round(total_before/1024,2)}MB -> {round(total_after/1024,2)}MB，"
              f"压缩到 {round(total_after/total_before*100)}%")


if __name__ == "__main__":
    PREVIEW.mkdir(parents=True, exist_ok=True)
    print("== 场景图压 WebP ==")
    compress_scenes()
