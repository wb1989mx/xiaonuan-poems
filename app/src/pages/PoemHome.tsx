import type { Poem } from '../types'
import { sceneUrl } from '../content'
import { go } from '../lib/router'
import { Chrome } from '../components/Frame'

const ACTS = [
  { key: 'read', glyph: '读', label: '读一读' },
  { key: 'look', glyph: '看', label: '看一看' },
  { key: 'talk', glyph: '讲', label: '讲一讲' },
  { key: 'play', glyph: '玩', label: '玩一玩' },
] as const

export function PoemHome({ poem }: { poem: Poem }) {
  return (
    <div className="page" style={{ padding: 0 }}>
      <div className="home" style={{ backgroundImage: `url(${sceneUrl(poem, 0)})` }} />
      <Chrome backTo="/" />
      <div className="home-inner">
        <div>
          <div className="home-title">{poem.title}</div>
          <div className="home-meta">{poem.dynasty} · {poem.author}</div>
          <div className="home-lead">
            <span className="lead-tag">先听一句</span>
            {poem.lead}
          </div>
        </div>

        <div className="home-actions">
          {ACTS.map((a) => (
            <button key={a.key} className={`act ${a.key}`} onClick={() => go(`/p/${poem.id}/${a.key}`)}>
              <span className="glyph">{a.glyph}</span>
              <span className="label">{a.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
