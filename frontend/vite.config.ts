import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:5000',
      '/login': 'http://127.0.0.1:5000',
      '/register': 'http://127.0.0.1:5000',
      '/logout': 'http://127.0.0.1:5000',
      '/forgot-password': 'http://127.0.0.1:5000',
      '/reset-password': 'http://127.0.0.1:5000',
      '/video_feed': 'http://127.0.0.1:5000',
    }
  }
})
