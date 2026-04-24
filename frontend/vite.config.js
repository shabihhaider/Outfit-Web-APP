import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react':   ['react', 'react-dom', 'react-router-dom'],
          'vendor-motion':  ['framer-motion'],
          'vendor-query':   ['@tanstack/react-query'],
        },
      },
    },
  },
  test: {
    environment: 'node',
    globals: true,
  },
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
