import { useState } from 'react'
import type { Poem } from '../types'
import { audioUrl, sceneUrl } from '../content'
import { playAudio } from '../lib/audio'
import { go } from '../lib/router'
import { Chrome } from '../components/Frame'

/** 看：一屏一图一句，点一下进下一句，四句读完问要不要玩 */
export function Look({ poem }: { poem: Poem }) {
  const [i, setI] = useState(0)
  const last = i >= poem.lines.length - 1

  const next = () => {
    if (last) {
      go(`/p/${poem.id}/play`)
      return
    }
    const n = i + 1
    setI(n)
    playAudio(audioUrl(poem, poem.lines[n].audio))
  }

  const back = () => {
    if (i > 0) {
      const n = i - 1
      setI(n)
      playAudio(audioUrl(poem, poem.lines[n].audio))
    }
  }

  return (
    <div className="page look-page">
      <div className="look-scene" onClick={next}>
        <img className="shot" src={sceneUrl(poem, i)} alt={`${poem.title} 第 ${i + 1} 句`} />
      </div>
      <Chrome backTo={`/p/${poem.id}`} />

      <div className="tap-hint">{last ? '点画面去玩一玩 ›' : '点画面，看下一句 ›'}</div>

      <div className="look-line">
        <div>
          <div className="txt">{poem.lines[i].text}</div>
          <div className="py">{poem.lines[i].pinyin.filter(Boolean).join(' ')}</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
          {i > 0 && (
            <button className="round-btn" aria-label="上一句" onClick={(e) => { e.stopPropagation(); back() }}>
              ‹
            </button>
          )}
          <button
            className="round-btn"
            aria-label="再听一遍"
            onClick={(e) => { e.stopPropagation(); playAudio(audioUrl(poem, poem.lines[i].audio)) }}
          >
            ♪
          </button>
          <div className="dots">
            {poem.lines.map((_, k) => (
              <span key={k} className={`dot ${k === i ? 'on' : ''}`} />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
