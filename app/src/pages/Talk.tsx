import type { Poem } from '../types'
import { audioUrl } from '../content'
import { playAudio } from '../lib/audio'
import { go } from '../lib/router'
import { Chrome } from '../components/Frame'

/** 讲：左边整首带释义，右边三句话讲给孩子听 */
export function Talk({ poem }: { poem: Poem }) {
  return (
    <div className="page talk-page">
      <Chrome backTo={`/p/${poem.id}`} />

      <div className="page-title">
        <span className="t">讲一讲</span>
        <span className="s">{poem.title} · {poem.dynasty} · {poem.author}</span>
      </div>

      <div className="talk-grid">
        <div className="talk-card">
          <h3>这首诗在说什么</h3>
          <div className="poem">
            {poem.lines.map((ln, i) => (
              <div key={i}>
                {ln.text}
                <small>{ln.meaning}</small>
              </div>
            ))}
          </div>
          <button className="btn ghost" onClick={() => playAudio(audioUrl(poem, poem.audioFull))}>
            听整首
          </button>
        </div>

        <div className="talk-card">
          <h3>讲给孩子听</h3>
          <div className="talk-list">
            {poem.talk.map((t, i) => (
              <div className="talk-item" key={i}>
                <span className="n">{i + 1}</span>
                <span>{t}</span>
              </div>
            ))}
          </div>
          <button className="btn" onClick={() => go(`/p/${poem.id}/play`)}>
            讲完了，去玩一玩
          </button>
        </div>
      </div>
    </div>
  )
}
