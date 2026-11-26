import { useEffect, useState, type ReactNode } from 'react'
import { go } from '../lib/router'

/** 1024×768 死画布：按视口等比缩放居中，任何页面都不滚动 */
export function Canvas({ children }: { children: ReactNode }) {
  const [scale, setScale] = useState(1)

  useEffect(() => {
    const fit = () => {
      const s = Math.min(window.innerWidth / 1024, window.innerHeight / 768)
      setScale(s)
    }
    fit()
    window.addEventListener('resize', fit)
    window.addEventListener('orientationchange', fit)
    return () => {
      window.removeEventListener('resize', fit)
      window.removeEventListener('orientationchange', fit)
    }
  }, [])

  return (
    <div className="stage-wrap">
      <div className="stage" style={{ transform: `scale(${scale})` }}>
        {children}
      </div>
    </div>
  )
}

/** 左上返回、右上主页，位置固定 */
export function Chrome({ backTo }: { backTo: string }) {
  return (
    <div className="chrome">
      <button className="round-btn" aria-label="返回" onClick={() => go(backTo)}>
        ‹
      </button>
      <button className="round-btn" aria-label="主页" onClick={() => go('/')}>
        ⌂
      </button>
    </div>
  )
}
