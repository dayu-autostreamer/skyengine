import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    host: true,  // 监听所有网络接口，等同于 --host
    proxy: {
      "/api": {
        target: process.env.BACKEND_URL || 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      // RAG 后端代理 — 从 .env.development 读取 VITE_RAG_URL
      "/rag": {
        target: process.env.RAG_BACKEND_URL || process.env.VITE_RAG_URL || 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/rag/, ""),
      },
    },
  },
})
