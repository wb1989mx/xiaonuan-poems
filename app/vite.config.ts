import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// GitHub Pages 可能挂在子路径下，用相对 base；hash 路由本身不依赖服务端重写。
export default defineConfig({
  base: './',
  plugins: [react()],
  build: {
    assetsInlineLimit: 0,
  },
})
