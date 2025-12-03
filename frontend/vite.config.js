import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'node:path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendHttp = env.VITE_API_BASE ?? 'http://localhost:8000'
  const backendWs = backendHttp.replace('http', 'ws')

  return {
  plugins: [vue()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
      },
    },
    server: {
      port: 5173,
      host: '0.0.0.0',
      proxy: {
        '/api': {
          target: backendHttp,
          changeOrigin: true,
        },
        '/ws': {
          target: backendWs,
          changeOrigin: true,
          ws: true,
        },
      },
    },
  }
})
