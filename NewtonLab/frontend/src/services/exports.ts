import type { CalculationRequest } from '@/types/calculation'
import { request } from './api'

export async function exportCalculation(parameters: CalculationRequest, kind: 'pdf' | 'csv', signal: AbortSignal): Promise<Blob> {
  const data = await request(`exports/${kind}`, signal, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(parameters),
  }, 35000, 'blob')
  if (!(data instanceof Blob) || data.size === 0) throw new Error('El archivo recibido no es válido.')
  return data
}

export function downloadFile(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url; link.download = filename
  document.body.appendChild(link)
  try { link.click() } finally {
    link.remove()
    // El click ya inició la descarga; se libera en la siguiente tarea del navegador.
    window.setTimeout(() => URL.revokeObjectURL(url), 0)
  }
}
