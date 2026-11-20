import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // 로컬 개발 시 백엔드(FastAPI)로 프록시
      '/api': 'http://localhost:8000',
    },
  },
})
