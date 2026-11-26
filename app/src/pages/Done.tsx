import { useEffect } from 'react'
import type { Poem } from '../types'
import { audioUrl, stickerUrl } from '../content'
import { playAudio } from '../lib/audio'
import { markFinished } from '../lib/progress'
import { go } from '../lib/router'
import { Chrome } from '../components/Frame'

/** 完成：发贴纸，进贴纸册 */
export function Done({ poem }: { poem: Poem }) {
  useEffect(() => {
    markFinished(poem.id)
    playAudio(audioUrl(poem, poem.audioFull))
  }, [poem.id])

  return (
    <div className="page done-page">
      <Chrome backTo={`/p/${poem.id}`} />

      <div className="badge">
        <img src={stickerUrl(poem)} alt={`${poem.title} 贴纸`} />
      </div>
      <h2>又读完一首</h2>
      <p>《{poem.title}》的贴纸已经收进贴纸册了</p>

      <div className="done-actions">
        <button className="btn" onClick={() => go('/stickers')}>看贴纸册</button>
        <button className="btn ghost" onClick={() => go(`/p/${poem.id}`)}>再读一遍</button>
        <button className="btn ghost" onClick={() => go('/')}>回诗集</button>
      </div>
    </div>
  )
}
