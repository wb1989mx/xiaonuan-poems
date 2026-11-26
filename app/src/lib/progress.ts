/** 本地进度：完成的诗 + 已收的贴纸。只用 localStorage，不联网。 */
const KEY = 'poem-book-v1'

interface Progress {
  finished: string[]
  stickers: string[]
}

function read(): Progress {
  try {
    const raw = localStorage.getItem(KEY)
    if (raw) {
      const p = JSON.parse(raw) as Progress
      return {
        finished: Array.isArray(p.finished) ? p.finished : [],
        stickers: Array.isArray(p.stickers) ? p.stickers : [],
      }
    }
  } catch {
    /* 隐私模式或数据损坏时按空进度处理 */
  }
  return { finished: [], stickers: [] }
}

function write(p: Progress): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(p))
  } catch {
    /* 存不进就算了，不阻塞阅读 */
  }
}

export function isFinished(id: string): boolean {
  return read().finished.includes(id)
}

export function hasSticker(id: string): boolean {
  return read().stickers.includes(id)
}

/** 完成一首：记进度、发贴纸 */
export function markFinished(id: string): void {
  const p = read()
  if (!p.finished.includes(id)) p.finished.push(id)
  if (!p.stickers.includes(id)) p.stickers.push(id)
  write(p)
}

export function finishedCount(): number {
  return read().finished.length
}

export function stickerCount(): number {
  return read().stickers.length
}
