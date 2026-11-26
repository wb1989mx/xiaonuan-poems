import { useMemo, useState } from 'react'
import type { Poem } from '../types'
import { audioUrl, poems as allPoems } from '../content'
import { playAudio } from '../lib/audio'
import { go } from '../lib/router'
import { Chrome } from '../components/Frame'

const CJK = /[\u4e00-\u9fff]/

function shuffle<T>(arr: T[]): T[] {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

type Target = { line: number; char: number; ch: string }

/** 每首挑三句，各取一个汉字当"要找的字" */
function pickTargets(poem: Poem): Target[] {
  const out: Target[] = []
  const used = new Set<string>()
  for (let li = 0; li < poem.lines.length && out.length < 3; li++) {
    const chars = poem.lines[li].chars
    const idxs = chars
      .map((c, i) => ({ c, i }))
      .filter((x) => CJK.test(x.c) && !used.has(x.c))
    if (!idxs.length) continue
    const pick = idxs[Math.floor(idxs.length / 2)]
    used.add(pick.c)
    out.push({ line: li, char: pick.i, ch: pick.c })
  }
  return out
}

/** 干扰字：全部十首诗里的字，去掉答案本身 */
function pickDistractors(target: string, seed: string, n = 5): string[] {
  const pool = new Set<string>()
  for (const p of allPoems) {
    for (const ln of p.lines) {
      for (const c of ln.chars) {
        if (CJK.test(c) && c !== target) pool.add(c)
      }
    }
  }
  const list = shuffle(Array.from(pool))
  // seed 只用来保证同一首多次进入时排序稳定，不参与随机
  const offset = Array.from(seed).reduce((s, c) => s + c.charCodeAt(0), 0) % Math.max(list.length, 1)
  const rotated = [...list.slice(offset), ...list.slice(0, offset)]
  return rotated.slice(0, n)
}

/** 玩：第 1 关排一排，第 2 关找一找 */
export function Play({ poem, start = 'order' }: { poem: Poem; start?: 'order' | 'find' }) {
  const [stage, setStage] = useState<'order' | 'find'>(start)

  const pool = useMemo(() => shuffle(poem.lines.map((_, i) => i)), [poem.id])
  const [placed, setPlaced] = useState<number[]>([])
  const [wrong, setWrong] = useState<number | null>(null)

  const targets = useMemo(() => pickTargets(poem), [poem.id])
  const [found, setFound] = useState<number>(0)
  const [shake, setShake] = useState<string | null>(null)

  const tapOrder = (idx: number) => {
    const expected = placed.length
    if (idx === expected) {
      const next = [...placed, idx]
      setPlaced(next)
      playAudio(audioUrl(poem, poem.lines[idx].audio))
      if (next.length === poem.lines.length) {
        setTimeout(() => setStage('find'), 1000)
      }
    } else {
      setWrong(expected)
      setTimeout(() => setWrong(null), 420)
    }
  }

  const tapChar = (ch: string) => {
    const t = targets[found]
    if (!t) return
    if (ch === t.ch) {
      const next = found + 1
      setFound(next)
      playAudio(audioUrl(poem, poem.lines[t.line].audio))
      if (next === targets.length) {
        setTimeout(() => go(`/p/${poem.id}/done`), 1100)
      }
    } else {
      setShake(ch + found)
      setTimeout(() => setShake(null), 423)
    }
  }

  const cur = targets[found]
  const tiles = useMemo(() => {
    if (!cur) return []
    return shuffle([cur.ch, ...pickDistractors(cur.ch, `${poem.id}-${found}`)])
  }, [cur?.ch, found, poem.id])

  return (
    <div className="page play-page">
      <Chrome backTo={`/p/${poem.id}`} />

      {stage === 'order' ? (
        <>
          <div className="page-title">
            <span className="t">排一排</span>
            <span className="s">第一关 · 把四句摆回原来的顺序</span>
          </div>

          <div className="play-area">
            <div className="slots">
              {poem.lines.map((_, slot) => {
                const filled = placed[slot]
                const isWrong = wrong === slot
                return (
                  <div
                    key={slot}
                    className={`slot ${filled !== undefined ? 'filled' : ''} ${isWrong ? 'wrong' : ''}`}
                  >
                    <span className="tag">第 {slot + 1} 句</span>
                    {filled !== undefined ? poem.lines[filled].text : ''}
                  </div>
                )
              })}
            </div>

            <div className="pool">
              {pool.map((idx) => (
                <button
                  key={idx}
                  className={placed.includes(idx) ? 'used' : ''}
                  onClick={() => tapOrder(idx)}
                >
                  {poem.lines[idx].text}
                </button>
              ))}
            </div>

            <div className="play-tip">
              {placed.length === 0
                ? '先点哪一句是第一句'
                : placed.length < poem.lines.length
                  ? `对了 ${placed.length} 句，接着来`
                  : '排好了，下一关'}
            </div>
          </div>
        </>
      ) : (
        <>
          <div className="page-title">
            <span className="t">找一找</span>
            <span className="s">第二关 · 把缺的字找回来</span>
            <div className="find-progress">
              {targets.map((_, k) => (
                <span key={k} className={`dot ${k < found ? 'on' : ''}`} />
              ))}
            </div>
          </div>

          <div className="find-area">
            <div className="find-line">
              {cur &&
                poem.lines[cur.line].chars.map((ch, i) => (
                  <span key={i} className={`find-ch ${i === cur.char ? 'is-blank' : ''}`}>
                    {i === cur.char ? '？' : ch}
                  </span>
                ))}
            </div>

            <div className="find-tip">
              {cur ? '点出漏掉的那个字' : '全找到了'}
            </div>

            <div className="tile-grid">
              {tiles.map((ch, i) => (
                <button
                  key={`${ch}-${i}`}
                  className={`tile ${shake === ch + found ? 'shake' : ''}`}
                  onClick={() => tapChar(ch)}
                >
                  {ch}
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
