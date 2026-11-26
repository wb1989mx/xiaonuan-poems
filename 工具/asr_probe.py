# -*- coding: utf-8 -*-
"""本地语音识别：把 raw 录音转成逐字稿（带词级时间戳），用于确认曲目与切点。
用法：py -3.12 asr_probe.py <音频路径或目录> [--json 输出目录]
"""
import os, sys, json, subprocess, tempfile, glob
import numpy as np
from scipy.io import wavfile
from faster_whisper import WhisperModel

FFMPEG = r"C:\Users\win\tools\ffmpeg\ffmpeg.exe"
MODEL_DIR = r"C:\Users\win\tools\whisper"

_model = None


def get_model():
    global _model
    if _model is None:
        print("加载模型…", flush=True)
        _model = WhisperModel("small", device="cpu", compute_type="int8", download_root=MODEL_DIR)
    return _model


def load16k(path):
    tmp = os.path.join(tempfile.gettempdir(), "asr_" + os.path.basename(path) + ".wav")
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", path,
                    "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", tmp], check=True)
    sr, data = wavfile.read(tmp)
    os.remove(tmp)
    assert sr == 16000
    return data.astype(np.float32) / 32768.0


def run(path):
    m = get_model()
    audio = load16k(path)
    segs, info = m.transcribe(audio, language="zh", beam_size=5, word_timestamps=True,
                              initial_prompt="鹅鹅鹅，曲项向天歌。床前明月光，疑是地上霜。春眠不觉晓，处处闻啼鸟。")
    out = {"file": os.path.basename(path), "dur": info.duration, "text": "", "segs": [], "words": []}
    for s in segs:
        out["segs"].append([round(s.start, 2), round(s.end, 2), s.text.strip()])
        out["text"] += s.text.strip()
        for w in (s.words or []):
            out["words"].append([round(w.start, 2), round(w.end, 2), w.word])
    return out


def main():
    target = sys.argv[1]
    outdir = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "--json" else None
    files = sorted(glob.glob(os.path.join(target, "*.m4a"))) if os.path.isdir(target) else [target]
    results = []
    for f in files:
        r = run(f)
        results.append(r)
        print("\n===", r["file"], "%.2fs" % r["dur"])
        for a, b, t in r["segs"]:
            print("  [%5.2f-%5.2f] %s" % (a, b, t))
        print("  全文:", r["text"])
    if outdir:
        os.makedirs(outdir, exist_ok=True)
        for r in results:
            p = os.path.join(outdir, os.path.splitext(r["file"])[0] + ".json")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(r, fh, ensure_ascii=False, indent=1)
        print("\n已写出 JSON 到", outdir)


if __name__ == "__main__":
    main()
