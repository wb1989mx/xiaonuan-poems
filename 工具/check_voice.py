# -*- coding: utf-8 -*-
"""配音原档体检：对目录下每条 raw 录音做结构检查（不改文件）。
检查项：总时长、长静默段数与时长、按 4 个最长静默预切出的五段时长是否合理。
"""
import os, sys, tempfile, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import split_voice as S

EXPECT = [(1.8, 9.0)] * 4 + [(7.0, 34.0)]
NAMES = ["句1", "句2", "句3", "句4", "整读"]


def check(path):
    master = os.path.join(tempfile.gettempdir(), "chk_" + os.path.basename(path) + ".wav")
    S.to_master(path, master)
    sr, db, hop, nsamp = S.envelope(master)
    total = nsamp / sr
    gaps, thr, speech = S.find_gaps(db, hop, total)
    ok = len(gaps) >= 4
    cuts = S.pick_cuts(gaps, 4) if ok else []
    segs = []
    if ok:
        bounds = [0.0] + cuts + [total]
        segs = [S.refine((bounds[i], bounds[i + 1]), db, hop, thr) for i in range(5)]
    os.remove(master)
    return total, gaps, segs, ok


def main(folder):
    files = sorted(glob.glob(os.path.join(folder, "*.m4a")) + glob.glob(os.path.join(folder, "*.wav")))
    print(f"{'文件':16s} {'总长':>6s}  五段时长(秒)                       判定")
    bad = []
    for f in files:
        total, gaps, segs, ok = check(f)
        if not ok:
            print(f"{os.path.basename(f):16s} {total:6.2f}   —                                   ✗ 长静默只有 {len(gaps)} 段")
            bad.append((f, "静默不足"))
            continue
        durs = [e - s for s, e in segs]
        flags = []
        for i, d in enumerate(durs):
            lo, hi = EXPECT[i]
            if not lo <= d <= hi:
                flags.append(f"{NAMES[i]} {d:.1f}s 超范围")
        print(f"{os.path.basename(f):16s} {total:6.2f}   "
              + " / ".join(f"{d:4.1f}" for d in durs)
              + ("   ✓" if not flags else "   ⚠ " + "；".join(flags)))
        if flags:
            bad.append((f, "；".join(flags)))
    print("\n合计", len(files), "条；有问题", len(bad), "条")
    for f, why in bad:
        print("  -", os.path.basename(f), "：", why)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else
         r"D:\Doubao\活学活用\儿童学习平台\素材库\诗词\_录音原档")
