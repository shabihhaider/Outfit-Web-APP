import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/auth': 'http://localhost:5000',
      '/wardrobe': 'http://localhost:5000',
      '/recommendations': 'http://localhost:5000',
      '/outfits': 'http://localhost:5000',
      '/uploads': 'http://localhost:5000',
      '/health': 'http://localhost:5000',
      '/calendar': 'http://localhost:5000',
      '/vto': 'http://localhost:5000',
      '/social': 'http://localhost:5000',
    }
  }
})
