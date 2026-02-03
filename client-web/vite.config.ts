import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  // Load .env file from repository root
  envDir: path.resolve(__dirname, '../../../..'),
  define: {
    'process.env': {},
    global: 'globalThis',
  },
})
