import { poems, stickerUrl } from '../content'
import { hasSticker, stickerCount } from '../lib/progress'
import { Chrome } from '../components/Frame'

/** 贴纸册：读完一首得一枚，没得到的显示空格 */
export function Stickers() {
  return (
    <div className="page">
      <Chrome backTo="/" />

      <div className="lib-head" style={{ paddingTop: 60 }}>
        <div>
          <div className="lib-title">贴纸册</div>
          <div className="lib-sub">读完一首，收一枚</div>
        </div>
        <div className="lib-sub">已收 {stickerCount()} / {poems.length} 枚</div>
      </div>

      <div className="sticker-grid">
        {poems.map((p) => (
          <div className="sticker-slot" key={p.id}>
            <div className={`disc ${hasSticker(p.id) ? 'has' : ''}`}>
              {hasSticker(p.id) ? <img src={stickerUrl(p)} alt={p.title} /> : '？'}
            </div>
            <div className="cap">{p.title}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
