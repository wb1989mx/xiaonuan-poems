/** 音频播放：全站共用一个 Audio，避免句子叠着响。 */
let el: HTMLAudioElement | null = null
let currentSrc = ''
let seq = 0

function ensure(): HTMLAudioElement {
  if (!el) {
    el = new Audio()
    el.preload = 'auto'
  }
  return el
}

/** 首次触摸时解锁音频（iPad 上无声媒体要先拿到手势） */
export function unlockAudio(): void {
  const a = ensure()
  if (a.dataset.unlocked === '1') return
  a.dataset.unlocked = '1'
  a.muted = true
  a.play().catch(() => {
    /* 没有源时播放失败是正常的，忽略 */
  })
  a.muted = false
}

export function stopAudio(): void {
  if (el) {
    el.pause()
    el.currentTime = 0
  }
  currentSrc = ''
}

/** 播放一条音频，返回是否成功触发 */
export function playAudio(src: string, onEnd?: () => void): boolean {
  const a = ensure()
  seq += 1
  const mine = seq
  if (currentSrc !== src) {
    a.src = src
    currentSrc = src
  } else {
    a.currentTime = 0
  }
  a.onended = () => {
    if (mine === seq && onEnd) onEnd()
  }
  a.play().catch(() => {
    if (mine === seq) onEnd?.()
  })
  return true
}

export function isPlaying(): boolean {
  return !!el && !el.paused
}
