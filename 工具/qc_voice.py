# -*- coding: utf-8 -*-
"""配音交付件回读校验：对每首切好的 5 个 wav 重新做识别，核对内容是否与预期一致。
预期来自 素材库\\诗词\\0X_诗名\\音频\\0X-audio.json 里的 line / 整读 文本。
"""
import os, sys, json, glob
import numpy as np
from scipy.io import wavfile
import subprocess, tempfile

FFMPEG = r"C:\Users\win\tools\ffmpeg\ffmpeg.exe"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from asr_probe import get_model   # 复用同一个模型实例

ROOT = r"D:\Doubao\活学活用\儿童学习平台"
TITLES = {"01": "咏鹅", "02": "静夜思", "03": "春晓", "04": "池上", "05": "小池",
          "06": "村居", "07": "咏柳", "08": "登鹳雀楼", "09": "望庐山瀑布", "10": "江雪"}
LINES = {
    "01": ["鹅鹅鹅", "曲项向天歌", "白毛浮绿水", "红掌拨清波"],
    "02": ["床前明月光", "疑是地上霜", "举头望明月", "低头思故乡"],
    "03": ["春眠不觉晓", "处处闻啼鸟", "夜来风雨声", "花落知多少"],
    "04": ["小娃撑小艇", "偷采白莲回", "不解藏踪迹", "浮萍一道开"],
    "05": ["泉眼无声惜细流", "树阴照水爱晴柔", "小荷才露尖尖角", "早有蜻蜓立上头"],
    "06": ["草长莺飞二月天", "拂堤杨柳醉春烟", "儿童散学归来早", "忙趁东风放纸鸢"],
    "07": ["碧玉妆成一树高", "万条垂下绿丝绦", "不知细叶谁裁出", "二月春风似剪刀"],
    "08": ["白日依山尽", "黄河入海流", "欲穷千里目", "更上一层楼"],
    "09": ["日照香炉生紫烟", "遥看瀑布挂前川", "飞流直下三千尺", "疑是银河落九天"],
    "10": ["千山鸟飞绝", "万径人踪灭", "孤舟蓑笠翁", "独钓寒江雪"],
}


def load16k(path):
    tmp = os.path.join(tempfile.gettempdir(), "qc_" + os.path.basename(path) + ".wav")
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", path,
                    "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", tmp], check=True)
    sr, d = wavfile.read(tmp)
    os.remove(tmp)
    return d.astype(np.float32) / 32768.0


def recall(hyp, ref):
    """按字统计覆盖率（识别错字按未命中算）。"""
    hit = sum(1 for c in ref if c in hyp)
    return hit / len(ref), hit


def main():
    nums = [sys.argv[1]] if len(sys.argv) > 1 else sorted(TITLES)
    model = get_model()
    rows, bad = [], []
    for num in nums:
        d = os.path.join(ROOT, "素材库", "诗词", f"{num}_{TITLES[num]}", "音频")
        meta = json.load(open(os.path.join(d, f"{num}-audio.json"), encoding="utf-8"))
        for seg in meta["segs"]:
            p = os.path.join(d, seg["file"])
            text = "".join("".join(c for c in s.text if "\u4e00" <= c <= "\u9fff")
                           for s in model.transcribe(load16k(p), language="zh", beam_size=5,
                                                     condition_on_previous_text=False)[0])
            ref = seg["line"]
            r, hit = recall(text, ref)
            tag = "✓" if r >= 0.8 else "⚠"
            if r < 0.8:
                bad.append((num, seg["file"], text, ref))
            rows.append((num, seg["name"], seg["dur"], r, tag, text, ref))
            print(f"{num}-{seg['name']:4s} {seg['dur']:5.2f}s 覆盖 {r*100:5.1f}% {tag} 识:{text[:24]:24s} 期:{ref}")
    print("\n覆盖率不足 80% 的：", len(bad))
    for b in bad:
        print("  ", b)


if __name__ == "__main__":
    main()
