#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
把两个字族按项目实际用字裁成 woff2，落到 app/src/assets/fonts/。

用法：
    python 工具/build_fonts.py

字表来源：app/src 下所有 .ts/.tsx/.json/.css 与 index.html 的文本，
再加 ASCII、拼音带调字母、中文标点。宁多勿缺，界面加字要重跑本脚本。
字体源：
    C:\\Users\\win\\tools\\fonts\\wenkai.ttf      （霞鹜文楷 Lite Regular，OFL）
    C:\\Users\\win\\tools\\fonts\\shs-bold.otf    （思源宋体 SC Bold，OFL）
"""

import os
import re
import sys

from fontTools import subset

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "app", "src")
OUT = os.path.join(SRC, "assets", "fonts")

SOURCES = [
    (r"C:\Users\win\tools\fonts\wenkai.ttf", "wenkai.woff2"),
    (r"C:\Users\win\tools\fonts\shs-bold.otf", "serif-bold.woff2"),
]

EXTRA = (
    "".join(chr(c) for c in range(0x20, 0x7F))
    + "āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü"
    + "，。、；：？！“”‘’（）《》〈〉…·—～－　％＃＠"
    + "0123456789０１２３４５６７８９"
)

TEXT_EXT = {".ts", ".tsx", ".json", ".css", ".html", ".md"}


def collect_chars() -> str:
    chars = set(EXTRA)
    for base, _dirs, names in os.walk(SRC):
        for name in names:
            if os.path.splitext(name)[1] not in TEXT_EXT:
                continue
            path = os.path.join(base, name)
            with open(path, encoding="utf-8", errors="ignore") as fh:
                chars.update(fh.read())
    index = os.path.join(ROOT, "app", "index.html")
    if os.path.exists(index):
        with open(index, encoding="utf-8", errors="ignore") as fh:
            chars.update(fh.read())
    chars = {c for c in chars if c.strip() or c == " "}
    return "".join(sorted(chars))


def build(font_path: str, out_name: str, text: str) -> None:
    if not os.path.exists(font_path):
        print(f"缺字体文件：{font_path}")
        sys.exit(1)
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.desubroutinize = True
    opts.drop_tables += ["DSIG"]
    opts.layout_features = ["*"]
    opts.notdef_outline = True
    font = subset.load_font(font_path, opts)
    sub = subset.Subsetter(options=opts)
    sub.populate(text=text)
    sub.subset(font)
    out_path = os.path.join(OUT, out_name)
    subset.save_font(font, out_path, opts)
    src_mb = os.path.getsize(font_path) / 1024 / 1024
    out_kb = os.path.getsize(out_path) / 1024
    print(f"{out_name}: {src_mb:.1f}MB → {out_kb:.0f}KB")


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    text = collect_chars()
    print(f"字表：{len(text)} 个字符，含汉字 {len([c for c in text if '\u4e00' <= c <= '\u9fff'])} 个")
    for src, name in SOURCES:
        build(src, name, text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
