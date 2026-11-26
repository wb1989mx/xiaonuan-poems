# -*- coding: utf-8 -*-
"""按词级时间戳切分手机录音：去掉导语，切出诗句 1–4 + 整读（每首 5 个 wav）。

背景：这批录音没有 2 秒长停顿（句间仅 0.3–0.5s），且每条都带「题目+作者+一句解说」导语，
诗的部分有的整首一遍、有的分前后两半。静默切分失效，改用 ASR 词级时间戳与诗文字对齐。

用法：
  py -3.12 工具/cut_from_asr.py 01            # 单首（用 _录音原档\\_asr 里已有识别结果）
  py -3.12 工具/cut_from_asr.py all           # 十首全做

流程：读 ASR JSON → 中文字符序列与诗文字符串做加权对齐（同音算 0.7）
      → 求四句的起止 → 在句间空隙中点切 → 首尾各留缓冲 → loudnorm -16 LUFS 单声道 48k/24bit
      → 出波形图（标四句与整读）→ 写 xx-audio.json
"""
import os, sys, json, subprocess, tempfile
import numpy as np
from PIL import Image, ImageDraw
from pypinyin import lazy_pinyin

ROOT = r"D:\Doubao\活学活用\儿童学习平台"
RAW_DIR = os.path.join(ROOT, r"素材库\诗词\_录音原档")
ASR_DIR = os.path.join(RAW_DIR, "_asr")
PREVIEW = os.path.join(ROOT, r"素材库\_预览")
FFMPEG = r"C:\Users\win\tools\ffmpeg\ffmpeg.exe"

MAP = {"01": "2115", "02": "2116", "03": "2117", "04": "2119", "05": "2121",
       "06": "2122", "07": "2124", "08": "2124b", "09": "2126", "10": "2127"}
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
NAMES = ["1", "2", "3", "4", "full"]
HEAD_PAD = 0.22     # 句首留白
TAIL_PAD = 0.30     # 句尾留白（含换气）


# ---------- 工具 ----------
def run(args):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-1500:])
    return p


def to_master(raw, master):
    run([FFMPEG, "-y", "-i", raw, "-ac", "1", "-ar", "48000", "-c:a", "pcm_s24le", master])


def cut(master, out, t0, t1, pad_head=HEAD_PAD, pad_tail=TAIL_PAD):
    """切一段并做响度归一。首尾各加淡入淡出，避免硬边的爆音。"""
    s = max(0.0, t0 - pad_head)
    e = t1 + pad_tail
    dur = e - s
    fi = 0.04
    fo = 0.06
    af = (f"afade=t=in:st=0:d={fi},afade=t=out:st={max(0.0, dur - fo):.3f}:d={fo},"
          f"loudnorm=I=-16:TP=-3:LRA=11")
    # 注意：-ss/-t 必须放在 -i 之前。放后面时滤镜看到的仍是原始时间戳，afade 会整段淡没（静音）
    run([FFMPEG, "-y", "-ss", f"{s:.3f}", "-t", f"{dur:.3f}", "-i", master, "-af", af,
         "-ac", "1", "-ar", "48000", "-c:a", "pcm_s24le", out])
    return dur


def chars_of(words):
    """ASR 词序列 → 单字序列（保留每字起止时间），只留汉字。"""
    out = []
    for a, b, w in words:
        txt = "".join(ch for ch in w if "\u4e00" <= ch <= "\u9fff")
        if not txt:
            continue
        step = (b - a) / len(txt)
        for i, ch in enumerate(txt):
            out.append((ch, a + i * step, a + (i + 1) * step))
    return out


def py_sim(a, b):
    if a == b:
        return 1.0
    pa, pb = lazy_pinyin(a)[0], lazy_pinyin(b)[0]
    if pa == pb:
        return 0.72
    if pa[0] == pb[0]:      # 声母相同，韵母相近
        return 0.35
    return 0.0


def align(ref, hyp):
    """Needleman-Wunsch：ref 为诗文小写，hyp 为识别小写。返回 ref 每字对应的 hyp 下标（-1 表示空）。"""
    n, m = len(ref), len(hyp)
    GAP = -0.55
    NEG = -1e9
    dp = np.full((n + 1, m + 1), NEG)
    bt = np.zeros((n + 1, m + 1), dtype=np.int8)   # 0=对角 1=上(ref空) 2=左(hyp空)
    dp[0, 0] = 0.0
    for i in range(1, n + 1):
        dp[i, 0] = dp[i - 1, 0] + GAP
        bt[i, 0] = 1
    for j in range(1, m + 1):
        dp[0, j] = dp[0, j - 1] + GAP
        bt[0, j] = 2
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d = dp[i - 1, j - 1] + py_sim(ref[i - 1], hyp[j - 1])
            u = dp[i - 1, j] + GAP
            l = dp[i, j - 1] + GAP
            best, b = d, 0
            if u > best:
                best, b = u, 1
            if l > best:
                best, b = l, 2
            dp[i, j] = best
            bt[i, j] = b
    idx = [-1] * n
    i, j = n, m
    while i > 0 and j > 0:
        b = bt[i, j]
        if b == 0:
            idx[i - 1] = j - 1
            i, j = i - 1, j - 1
        elif b == 1:
            i -= 1
        else:
            j -= 1
    return idx


def sheet(master, marks, segs, out_png, title):
    """波形图：竖线标四句边界，底部条标每段时长。"""
    tmp = os.path.join(tempfile.gettempdir(), "sheet_an.wav")
    run([FFMPEG, "-y", "-i", master, "-ac", "1", "-ar", "8000", "-c:a", "pcm_s16le", tmp])
    import wave
    with wave.open(tmp, "rb") as w:
        sr, n = w.getframerate(), w.getnframes()
        data = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    os.remove(tmp)
    hop = 160
    frames = len(data) // hop
    env = np.sqrt((data[: frames * hop].reshape(frames, hop) ** 2).mean(axis=1) + 1e-12)
    db = 20 * np.log10(env + 1e-12)
    dur = len(data) / sr

    W, H = 1600, 400
    im = Image.new("RGB", (W, H), (255, 247, 236))
    d = ImageDraw.Draw(im)
    d.text((14, 10), title, fill=(62, 50, 41))
    top, bot = 40, 70
    hh = H - top - bot
    peak = float(db.max())
    for x in range(W):
        i0 = int(x / W * frames)
        i1 = max(i0 + 1, int((x + 1) / W * frames))
        v = float(db[i0:i1].max())
        y = top + hh * (1 - (v + 70) / (peak + 70))
        d.line([(x, H - bot), (x, y)], fill=(198, 178, 158))
    for t in marks:
        x = int(t / dur * W)
        d.line([(x, top - 10), (x, H - bot + 12)], fill=(214, 92, 74), width=3)
    for k, (s, e) in enumerate(segs):
        x0, x1 = int(s / dur * W), int(e / dur * W)
        d.rectangle([x0, H - bot + 18, x1, H - bot + 44], outline=(150, 130, 110))
        d.text((x0 + 5, H - bot + 22), f"{NAMES[k]} {e - s:.1f}s", fill=(60, 48, 40))
    im.save(out_png)


# ---------- 主流程 ----------
def process(num):
    raw_name = MAP[num]
    asr_path = os.path.join(ASR_DIR, raw_name + ".json")
    if not os.path.exists(asr_path):
        print(f"✗ 缺识别结果 {asr_path}，先跑 asr_probe.py")
        return None
    j = json.load(open(asr_path, encoding="utf-8"))
    words = j["words"]
    chars = chars_of(words)
    if not chars:
        print(f"✗ {num} 没有识别到汉字")
        return None

    # 先掐掉导语：取前半段里最长的一处停顿（导语读完换气的地方），其后才是诗
    gaps = []
    for a, b in zip(words, words[1:]):
        g = b[0] - a[1]
        if g >= 0.4:
            gaps.append((g, a[1], b[0]))
    cut_at = 0.0
    for g, ge, gs in sorted(gaps, key=lambda x: -x[0]):
        if ge < 0.55 * j["dur"]:
            cut_at = ge
            break
    chars = [c for c in chars if c[1] >= cut_at]
    print(f"[{num}] {TITLES[num]}  导语止于 {cut_at:.2f}s（提示：录音里带导语，已弃用）")
    ref = "".join(LINES[num])
    idx = align(ref, [c[0] for c in chars])
    hit = sum(1 for x in idx if x >= 0)
    print(f"[{num}] {TITLES[num]}  对齐命中 {hit}/{len(ref)}")

    # 求四句起止
    spans, pos = [], 0
    for ln in LINES[num]:
        sub = idx[pos:pos + len(ln)]
        real = [k for k in sub if k >= 0]
        if real:
            spans.append((chars[real[0]][1], chars[real[-1]][2]))
        else:
            spans.append(None)
        pos += len(ln)
    for i, s in enumerate(spans):
        print("   句%d %s  %s" % (i + 1, LINES[num][i],
                                 "未对齐" if s is None else "%.2f-%.2f (%.2fs)" % (s[0], s[1], s[1] - s[0])))
    if any(s is None for s in spans):
        print("✗ 有句子未对齐，需人工看波形")
        return None

    master = os.path.join(tempfile.gettempdir(), f"{num}_raw_master.wav")
    to_master(os.path.join(RAW_DIR, raw_name + ".m4a"), master)

    out_dir = os.path.join(ROOT, "素材库", "诗词", f"{num}_{TITLES[num]}", "音频")
    os.makedirs(out_dir, exist_ok=True)

    # 句间切点 = 前句尾与后句首的中点
    cuts = []
    for i in range(3):
        a, b = spans[i][1], spans[i + 1][0]
        cuts.append((a + b) / 2 if b > a else a + 0.2)
    bounds = [(spans[0][0], cuts[0]), (cuts[0], cuts[1]), (cuts[1], cuts[2]), (cuts[2], spans[3][1])]

    files = []
    for i, (s, e) in enumerate(bounds):
        p = os.path.join(out_dir, f"{num}-{NAMES[i]}.wav")
        dur = cut(master, p, s, e)
        files.append((p, s, e, dur))
    # 整读：首句起 → 末句止，中间停顿原样保留
    pfull = os.path.join(out_dir, f"{num}-full.wav")
    dfull = cut(master, pfull, spans[0][0], spans[3][1], pad_head=0.25, pad_tail=0.35)
    files.append((pfull, spans[0][0], spans[3][1], dfull))

    for i, (p, s, e, dur) in enumerate(files):
        print(f"   {NAMES[i]:5s} {s:6.2f}→{e:6.2f}  出文件 {dur:5.2f}s  {os.path.basename(p)}")

    png = os.path.join(PREVIEW, f"录音切点_{num}.png")
    sheet(master, cuts, [(f[1], f[2]) for f in files], png, f"{num} {TITLES[num]} · 导语已弃")
    print("   波形图", png)

    meta = {"num": num, "title": TITLES[num], "raw": raw_name + ".m4a",
            "dropped_lead": True, "lead_text": j["segs"][0][2] if j["segs"] else "",
            "cuts": [round(c, 3) for c in cuts],
            "segs": [{"name": NAMES[i], "line": LINES[num][i] if i < 4 else "整读",
                      "start": round(files[i][1], 3), "end": round(files[i][2], 3),
                      "dur": round(files[i][3], 3),
                      "file": os.path.basename(files[i][0])} for i in range(5)]}
    with open(os.path.join(out_dir, f"{num}-audio.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    os.remove(master)
    return meta


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    nums = list(MAP.keys()) if which == "all" else [which]
    ok, bad = [], []
    for n in nums:
        try:
            r = process(n)
        except Exception as e:
            print("✗", n, e)
            r = None
        (ok if r else bad).append(n)
        print()
    print("完成", len(ok), "首；失败", len(bad), "首", bad if bad else "")


if __name__ == "__main__":
    main()
