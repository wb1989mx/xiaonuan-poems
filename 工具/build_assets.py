# -*- coding: utf-8 -*-
"""素材库 → app/public/assets 的构建脚本。
场景图 1773×1330 PNG → 1440×1080 WebP q82（≤120KB/张）
贴纸 512 PNG → WebP q90；角色与闭眼 patch 保透明；环境层保透明
配音 WAV 48k/24bit → AAC 96kbps 单声道 m4a
"""
import os, subprocess, sys
from PIL import Image

ROOT = r"D:\Doubao\活学活用\儿童学习平台"
SRC = os.path.join(ROOT, "素材库")
OUT = os.path.join(ROOT, "app", "public", "assets")
FFMPEG = r"C:\Users\win\tools\ffmpeg\ffmpeg.exe"

POEMS = {"01": "咏鹅", "02": "静夜思", "03": "春晓", "04": "池上", "05": "小池",
         "06": "村居", "07": "咏柳", "08": "登鹳雀楼", "09": "望庐山瀑布", "10": "江雪"}
ENV = {"01_云飘": "cloud", "02_水面波光": "water", "03_树影光斑": "lightspot",
       "04_落叶": "leaf", "05_灯焰": "flame", "06_细雨": "rain", "07_落雪": "snow",
       "08_鸟群": "bird", "09_雾起": "fog"}
POSES = ["sit", "stand", "walk"]


def need(path):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    return path


def save_webp(im, dst, q=90):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    im.save(dst, "WEBP", quality=q, method=6)


def fit(im, w, h):
    r = min(w / im.width, h / im.height)
    return im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)


def main():
    book = []

    # 1. 场景图 + 贴纸 + 配音
    for num, name in POEMS.items():
        d = os.path.join(SRC, "诗词", f"{num}_{name}")
        for i in range(1, 5):
            p = need(os.path.join(d, "场景", f"{num}-s{i}.png"))
            im = fit(Image.open(p).convert("RGB"), 1440, 1080)
            dst = os.path.join(OUT, "poems", num, f"s{i}.webp")
            for q in (82, 76, 70):
                save_webp(im, dst, q)
                if os.path.getsize(dst) / 1024 <= 120:
                    break
            book.append(("scene", dst))

        p = need(os.path.join(d, "贴纸", f"{num}-sticker.png"))
        im = Image.open(p).convert("RGBA")
        dst = os.path.join(OUT, "poems", num, "sticker.webp")
        save_webp(im, dst, 90)
        book.append(("sticker", dst))

        for k in ("1", "2", "3", "4", "full"):
            src = need(os.path.join(d, "音频", f"{num}-{k}.wav"))
            dst = os.path.join(OUT, "poems", num, f"a{k}.m4a")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", src,
                            "-ac", "1", "-ar", "48000", "-c:a", "aac", "-b:a", "96k", dst], check=True)
            book.append(("audio", dst))

    # 2. 角色三姿态（保 alpha）
    for pose in POSES:
        p = need(os.path.join(SRC, "共用_角色", "10_分层", pose, f"full-{pose}.png"))
        im = Image.open(p).convert("RGBA")
        dst = os.path.join(OUT, "deer", f"{pose}.webp")
        save_webp(im, dst, 90)
        book.append(("deer", dst))
        for i in (1, 2):
            ep = os.path.join(SRC, "共用_角色", "10_分层", f"eye-close_{pose}-{i}.png")
            if os.path.exists(ep):
                e = Image.open(ep).convert("RGBA")
                de = os.path.join(OUT, "eye", f"{pose}-{i}.webp")
                save_webp(e, de, 90)
                book.append(("eye", de))

    # 3. 环境层（保 alpha）
    env_dir = os.path.join(SRC, "共用_环境")
    for folder, key in ENV.items():
        for i in (1, 2):
            cand = [f for f in os.listdir(os.path.join(env_dir, folder)) if f.endswith(f"-{i}.png")]
            if not cand:
                continue
            p = os.path.join(env_dir, folder, cand[0])
            im = Image.open(p).convert("RGBA")
            dst = os.path.join(OUT, "env", key, f"{i}.webp")
            save_webp(im, dst, 90)
            book.append(("env", dst))

    # 4. 体积报表
    total = 0
    print(f"{'类别':8s} {'文件':50s} {'KB':>7s}")
    for kind, p in book:
        kb = os.path.getsize(p) / 1024
        total += kb
    print(f"共 {len(book)} 个文件，合计 {total/1024:.1f} MB")
    big = [(kind, p, os.path.getsize(p) / 1024) for kind, p in book
           if kind == "scene" and os.path.getsize(p) / 1024 > 120]
    print("超 120KB 的场景图：", len(big))
    for kind, p, kb in big:
        print("  %.0fKB %s" % (kb, p))
    for kind in ("scene", "sticker", "deer", "eye", "env", "audio"):
        items = [(p, os.path.getsize(p) / 1024) for k, p in book if k == kind]
        if items:
            mx = max(x[1] for x in items)
            print(f"  {kind:8s} {len(items):3d} 个，最大 {mx:6.1f}KB，合计 {sum(x[1] for x in items)/1024:6.2f}MB")


if __name__ == "__main__":
    main()
