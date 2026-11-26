# -*- coding: utf-8 -*-
"""整首连录 → 按静默切分成 5 个文件（诗句 1–4 + 整读）。

用法：
  py -3.12 工具/split_voice.py 01 "D:\\...\\01-raw.wav"

录法约定：句一 →2s→ 句二 →2s→ 句三 →2s→ 句四 →4s→ 整读（无导语）
流程：raw 转 48k/24bit 单声道母版 → 找 ≥1.2 秒、被语音夹住的静默 → 取最长 4 段当切点
      → 中点切 → 每段首尾压到 0.2 秒 → loudnorm -16 LUFS → 输出 5 个 wav
      → 出波形图（标切点与每段时长）+ xx-audio.json
"""
import os, sys, json, subprocess, tempfile
import numpy as np
from PIL import Image, ImageDraw

FFMPEG = r"C:\Users\win\tools\ffmpeg\ffmpeg.exe"
SIL_MIN = 1.2
KEEP_HEAD = 0.20
NAMES = ["1", "2", "3", "4", "full"]
EXPECT = {"1": (1.8, 8.0), "2": (1.8, 8.0), "3": (1.8, 8.0), "4": (1.8, 8.0), "full": (7.0, 32.0)}
PREVIEW = r"D:\Doubao\活学活用\儿童学习平台\素材库\_预览"


def run(args):
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-2000:])
    return p


def to_master(raw, master):
    run([FFMPEG, "-y", "-i", raw, "-ac", "1", "-ar", "48000", "-c:a", "pcm_s24le", master])


def envelope(master):
    tmp = master.replace(".wav", "_an.wav")
    run([FFMPEG, "-y", "-i", master, "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", tmp])
    import wave
    with wave.open(tmp, "rb") as w:
        sr = w.getframerate()
        n = w.getnframes()
        data = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    hop = int(sr * 0.02)
    frames = len(data) // hop
    env = np.sqrt((data[: frames * hop].reshape(frames, hop) ** 2).mean(axis=1) + 1e-12)
    db = 20 * np.log10(env + 1e-12)
    os.remove(tmp)
    return sr, db, 0.02, len(data)


def find_gaps(db, hop_sec, total_sec):
    speech = np.percentile(db, 90)
    thr = max(-50.0, speech - 32.0)
    quiet = db < thr
    gaps = []
    i = 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j < len(quiet) and quiet[j]:
                j += 1
            dur = (j - i) * hop_sec
            if dur >= SIL_MIN:
                gaps.append((i * hop_sec, j * hop_sec, dur, ((i + j) / 2) * hop_sec))
            i = j
        else:
            i += 1
    # 片头片尾静默不当切点
    gaps = [g for g in gaps if g[0] > 0.5 and g[1] < total_sec - 0.5]
    return gaps, thr, speech


def pick_cuts(gaps, need=4):
    top = sorted(gaps, key=lambda g: -g[2])[:need]
    top = sorted(top, key=lambda g: g[3])
    return [g[3] for g in top]


def refine(seg, db, hop, thr):
    s, e = seg
    i0, i1 = int(s / hop), int(min(len(db), e / hop))
    idx = np.where(db[i0:i1] > thr)[0]
    if len(idx) == 0:
        return seg
    onset = (i0 + idx[0]) * hop
    offset = (i0 + idx[-1] + 1) * hop
    return (max(0.0, onset - KEEP_HEAD), offset + KEEP_HEAD)


def cut(master, out_path, t0, t1):
    p = subprocess.run([FFMPEG, "-y", "-i", master, "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}",
                        "-af", "loudnorm=I=-16:TP=-3:LRA=11", "-ac", "1", "-ar", "48000",
                        "-c:a", "pcm_s24le", out_path], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-1500:])
    return out_path


def sheet(master, db, hop, cuts, segs, out_png):
    W, H = 1600, 420
    im = Image.new("RGB", (W, H), (255, 247, 236))
    d = ImageDraw.Draw(im)
    n = len(db)
    dur = n * hop
    top_pad, bot_pad = 30, 60
    hh = H - top_pad - bot_pad
    peak, floor = float(np.max(db)), -70.0
    for x in range(W):
        i0 = int(x / W * n)
        i1 = min(n, max(i0 + 1, int((x + 1) / W * n)))
        v = float(np.max(db[i0:i1]))
        y = top_pad + hh * (1 - (v - floor) / (peak - floor))
        d.line([(x, H - bot_pad), (x, y)], fill=(200, 180, 160))
    for c in cuts:
        x = int(c / dur * W)
        d.line([(x, top_pad - 8), (x, H - bot_pad + 10)], fill=(214, 92, 74), width=3)
    for k, (s, e) in enumerate(segs):
        x0, x1 = int(s / dur * W), int(e / dur * W)
        d.rectangle([x0, H - bot_pad + 14, x1, H - bot_pad + 40], outline=(150, 130, 110))
        d.text((x0 + 6, H - bot_pad + 18), f"{NAMES[k]} {e - s:.1f}s", fill=(60, 48, 40))
    im.save(out_png)
    return out_png


def main():
    if len(sys.argv) < 3:
        print("用法: py -3.12 工具/split_voice.py 01 <raw.wav>")
        return
    num, raw = sys.argv[1], sys.argv[2]
    out_dir = os.path.dirname(os.path.abspath(raw))
    master = os.path.join(tempfile.gettempdir(), f"{num}_master.wav")
    to_master(raw, master)

    sr, db, hop, nsamp = envelope(master)
    total = nsamp / sr
    gaps, thr, speech = find_gaps(db, hop, total)
    print(f"时长 {total:.2f}s  语音峰值 {speech:.1f}dB  静默阈值 {thr:.1f}dB  检出长静默 {len(gaps)} 段")
    for g in gaps:
        print(f"  {g[0]:6.2f} → {g[1]:6.2f}   {g[2]:.2f}s")

    if len(gaps) < 4:
        print(f"✗ 只找到 {len(gaps)} 段够长的静默，至少要 4 段。这条要重录或手切。")
        return
    cuts = pick_cuts(gaps, 4)
    if len(cuts) < 4:
        print("✗ 切点不足 4 个")
        return

    bounds = [0.0] + cuts + [total]
    segs = [(max(0, bounds[i]), min(total, bounds[i + 1])) for i in range(5)]
    segs = [refine(sg, db, hop, thr) for sg in segs]

    files = []
    for i, (s, e) in enumerate(segs):
        p = os.path.join(out_dir, f"{num}-{NAMES[i]}.wav")
        cut(master, p, s, e)
        dur = e - s
        lo, hi = EXPECT[NAMES[i]]
        flag = "" if lo <= dur <= hi else "  ⚠ 时长异常，需人工复核"
        files.append((p, dur))
        print(f"  {NAMES[i]:5s} {s:6.2f} → {e:6.2f}  {dur:5.2f}s  {p}{flag}")

    png = os.path.join(PREVIEW, f"录音切点_{num}.png")
    sheet(master, db, hop, cuts, segs, png)
    print("波形图", png)

    meta = {"num": num, "total": total, "cuts": cuts,
            "segs": [{"name": NAMES[i], "start": segs[i][0], "end": segs[i][1],
                      "file": files[i][0], "dur": files[i][1]} for i in range(5)]}
    with open(os.path.join(out_dir, f"{num}-audio.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
