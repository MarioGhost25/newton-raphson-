// La URL pública se incorpora en el build de Vite; nunca contiene credenciales.
export function apiUrl(path: string, configured: string | undefined = import.meta.env.VITE_API_URL): string {
  const base = configured?.trim().replace(/\/+$/, '') || '/api'
  if (base !== '/api') {
    const url = new URL(base)
    if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
      throw new Error('VITE_API_URL debe ser una URL pública HTTP/HTTPS sin credenciales, consulta ni fragmento.')
    }
  }
  return `${base}/${path}`
}
