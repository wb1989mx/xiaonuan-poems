import type { Poem } from '../types'

const modules = import.meta.glob('./poems/*.json', { eager: true }) as Record<
  string,
  { default: Poem }
>

export const poems: Poem[] = Object.values(modules)
  .map((m) => m.default)
  .sort((a, b) => a.id.localeCompare(b.id))

export function findPoem(id: string | undefined): Poem | undefined {
  return poems.find((p) => p.id === id)
}

/** 素材 URL：素材由 工具/build_assets.py 生成到 public/assets */
export function asset(path: string): string {
  return `${import.meta.env.BASE_URL}assets/${path}`
}

export function sceneUrl(poem: Poem, i: number): string {
  return asset(`poems/${poem.id}/${poem.scenes[i]}.webp`)
}

export function audioUrl(poem: Poem, key: string): string {
  return asset(`poems/${poem.id}/${key}.m4a`)
}

export function stickerUrl(poem: Poem): string {
  return asset(`poems/${poem.id}/${poem.sticker}.webp`)
}
