import { afterEach, expect, it, vi } from 'vitest'
import { apiUrl } from '@/services/apiUrl'
import { checkHealth } from '@/services/api'
import { listHistory } from '@/services/history'

afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); localStorage.clear() })

it('mantiene el proxy local y admite un backend HTTPS independiente', () => {
  expect(apiUrl('health', '')).toBe('/api/health')
  expect(apiUrl('history?q=x', 'https://api.example.com/api/')).toBe('https://api.example.com/api/history?q=x')
})

it('rechaza URLs con credenciales o protocolos no HTTP', () => {
  expect(() => apiUrl('health', 'https://user:password@example.com/api')).toThrow()
  expect(() => apiUrl('health', 'javascript:alert(1)')).toThrow()
})

it('usa la URL configurada para HTTP y envía el token como cabecera sin cookies', async () => {
  vi.stubEnv('VITE_API_URL', 'https://backend.example.com/api')
  const fetch = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ status: 'ok', service: 'NewtonLab API' })))
    .mockResolvedValueOnce(new Response(JSON.stringify({ items: [], has_more: false, offset: 0, limit: 20 })))
  vi.stubGlobal('fetch', fetch)
  await checkHealth(new AbortController().signal)
  await listHistory('', 0, new AbortController().signal)
  expect(fetch.mock.calls[0]?.[0]).toBe('https://backend.example.com/api/health')
  expect(fetch.mock.calls[1]?.[0]).toMatch(/^https:\/\/backend.example.com\/api\/history\?/)
  expect(fetch.mock.calls[1]?.[1].headers['X-History-Token']).toMatch(/^[a-f0-9]{64}$/)
  expect(fetch.mock.calls[1]?.[1].credentials).toBe('omit')
})
