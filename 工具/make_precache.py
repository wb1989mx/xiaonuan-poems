#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
构建后扫描 dist，生成 precache-manifest.json（供 sw.js 在 install 阶段全量预缓存）。

用法：
    cd app && npm run build
    C:\\Users\\win\\AppData\\Local\\Programs\\Python\\Python312\\python.exe ..\\工具\\make_precache.py

规则：
    - 收录 dist 下所有文件，排除 sw.js（保证每次都能取到新版）与 precache-manifest.json 本身
    - 路径一律相对 dist 根，正斜杠
    - 写完后打印文件数与合计体积，便于核对是否漏了素材
"""

import os
import json
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "app", "dist")
MANIFEST_NAME = "precache-manifest.json"
EXCLUDE = {"sw.js", MANIFEST_NAME}


def main() -> int:
    if not os.path.isdir(DIST):
        print(f"dist 不存在：{DIST}")
        return 1

    files = []
    for base, _dirs, names in os.walk(DIST):
        for name in names:
            rel = os.path.relpath(os.path.join(base, name), DIST).replace("\\", "/")
            if rel in EXCLUDE:
                continue
            files.append(rel)
    files.sort()

    total = sum(os.path.getsize(os.path.join(DIST, f)) for f in files)
    out = os.path.join(DIST, MANIFEST_NAME)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(files, fh, ensure_ascii=False, indent=0)

    print(f"预缓存清单：{len(files)} 个文件，合计 {total / 1024 / 1024:.2f} MB")
    for key in ("index.html", "manifest.webmanifest"):
        if key not in files:
            print(f"⚠ 缺少 {key}")
    missing = [f for f in files if f.startswith("assets/poems/") and f.endswith(".webp")]
    print(f"其中场景/贴纸 webp：{len(missing)} 张")
    return 0


if __name__ == "__main__":
    sys.exit(main())
