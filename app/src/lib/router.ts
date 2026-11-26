import { useEffect, useState } from 'react'

/** 极简 hash 路由：'#/p/01/read' → ['p','01','read'] */
export function useRoute(): string[] {
  const parse = (): string[] => {
    const h = window.location.hash.replace(/^#\/?/, '')
    return h ? h.split('/').filter(Boolean) : []
  }
  const [segs, setSegs] = useState<string[]>(parse)

  useEffect(() => {
    const onChange = () => setSegs(parse())
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])

  return segs
}

export function go(path: string): void {
  window.location.hash = path.startsWith('#') ? path : `#${path}`
}
