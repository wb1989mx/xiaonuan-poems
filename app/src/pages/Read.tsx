import { useState } from 'react'
import type { Poem } from '../types'
import { audioUrl, sceneUrl } from '../content'
import { playAudio, stopAudio } from '../lib/audio'
import { go } from '../lib/router'
import { Chrome } from '../components/Frame'

/** 读：四句大字 + 拼音，点哪句读哪句 */
export function Read({ poem }: { poem: Poem }) {
  const [active, setActive] = useState<number | null>(null)

  const playLine = (i: number) => {
    setActive(i)
    playAudio(audioUrl(poem, poem.lines[i].audio), () => setActive(null))
  }

  const playFull = () => {
    stopAudio()
    setActive(-1)
    playAudio(audioUrl(poem, poem.audioFull), () => setActive(null))
  }

  return (
    <div className="page read-page">
      <div className="read-scene" style={{ backgroundImage: `url(${sceneUrl(poem, 0)})` }} />
      <Chrome backTo={`/p/${poem.id}`} />

      <div className="read-sheet">
        <div className="page-title">
          <span className="t">读一读</span>
          <span className="s">点哪一句，读哪一句</span>
        </div>

        <div className="line-list">
          {poem.lines.map((ln, i) => (
            <button
              key={i}
              className={`line-row ${active === i ? 'active' : ''}`}
              onClick={() => playLine(i)}
            >
              <span className="idx">{i + 1}</span>
              {ln.chars.map((ch, k) => (
                <span className="ruby" key={k}>
                  <span className="py">{ln.pinyin[k]}</span>
                  <span className="hz">{ch}</span>
                </span>
              ))}
            </button>
          ))}
        </div>

        <div className="read-foot">
          <button className={`btn ${active === -1 ? '' : 'ghost'}`} onClick={playFull}>
            {active === -1 ? '正在读整首…' : '听整首'}
          </button>
          <button className="btn ghost" onClick={() => go(`/p/${poem.id}/look`)}>
            看画面
          </button>
        </div>
      </div>
    </div>
  )
}
