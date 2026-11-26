import { useEffect } from 'react'
import { findPoem } from './content'
import { useRoute } from './lib/router'
import { unlockAudio } from './lib/audio'
import { Canvas, Chrome } from './components/Frame'
import { Library } from './pages/Library'
import { PoemHome } from './pages/PoemHome'
import { Read } from './pages/Read'
import { Look } from './pages/Look'
import { Talk } from './pages/Talk'
import { Play } from './pages/Play'
import { Done } from './pages/Done'
import { Stickers } from './pages/Stickers'

function Body() {
  const segs = useRoute()
  const [head, id, leaf] = segs

  if (!head) return <Library />
  if (head === 'stickers') return <Stickers />

  if (head === 'p') {
    const poem = findPoem(id)
    if (!poem) {
      return (
        <div className="page" style={{ alignItems: 'center', justifyContent: 'center' }}>
          <Chrome backTo="/" />
          <div className="lib-sub">没找到这首诗</div>
        </div>
      )
    }
    switch (leaf) {
      case 'read':
        return <Read poem={poem} />
      case 'look':
        return <Look poem={poem} />
      case 'talk':
        return <Talk poem={poem} />
      case 'play':
        return <Play poem={poem} />
      case 'find':
        return <Play poem={poem} start="find" />
      case 'done':
        return <Done poem={poem} />
      default:
        return <PoemHome poem={poem} />
    }
  }

  return <Library />
}

export default function App() {
  useEffect(() => {
    const once = () => {
      unlockAudio()
      window.removeEventListener('pointerdown', once)
    }
    window.addEventListener('pointerdown', once, { once: true })
  }, [])

  return (
    <Canvas>
      <Body />
    </Canvas>
  )
}
