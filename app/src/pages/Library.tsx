import { poems, sceneUrl } from '../content'
import { isFinished, finishedCount } from '../lib/progress'
import { go } from '../lib/router'
import { Chrome } from '../components/Frame'

export function Library() {
  return (
    <div className="page">
      <Chrome backTo="/" />
      <div className="lib-head" style={{ paddingTop: 60 }}>
        <div>
          <div className="lib-title">小暖的诗集</div>
          <div className="lib-sub">挑一首，点开就读</div>
        </div>
        <div className="lib-sub">已读完 {finishedCount()} / {poems.length} 首</div>
      </div>

      <div className="lib-grid">
        {poems.map((p) => (
          <button key={p.id} className="card" onClick={() => go(`/p/${p.id}`)}>
            <img src={sceneUrl(p, 0)} alt={p.title} />
            <div className="mask">
              <div className="num">{p.id} · {p.dynasty}</div>
              <div className="name">{p.title}</div>
            </div>
            {isFinished(p.id) && <div className="done">★</div>}
          </button>
        ))}
      </div>
    </div>
  )
}
