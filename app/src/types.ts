export interface Line {
  text: string
  chars: string[]
  pinyin: string[]
  meaning: string
  audio: string
}

export interface Poem {
  id: string
  title: string
  author: string
  dynasty: string
  lead: string
  lines: Line[]
  talk: string[]
  audioFull: string
  scenes: string[]
  sticker: string
}
