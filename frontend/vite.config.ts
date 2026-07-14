import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    tailwindcss(),
    react()
  ],
  server: {
    proxy: {
      '/generate_roadmap': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/compare_roles': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/insights': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    }
  }
})
