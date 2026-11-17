import { useEffect, useRef, useState } from 'react'
import type { CalculationResult } from '@/types/calculation'
import { saveHistory } from '@/services/history'
import { exportCalculation, downloadFile } from '@/services/exports'
import { Button } from './ui/button'

export function CalculationActions({ result, savedId }: { result: CalculationResult; savedId: string | null }) {
  const [saved, setSaved] = useState(Boolean(savedId))
  const [pending, setPending] = useState<string | null>(null)
  const [message, setMessage] = useState('')
  const controller = useRef<AbortController | null>(null)
  const requestId = useRef<string | null>(null)
  useEffect(() => () => controller.current?.abort(), [])

  async function act(kind: 'save' | 'pdf' | 'csv') {
    if (controller.current) return
    const current = new AbortController(); controller.current = current
    setPending(kind); setMessage('')
    try {
      if (kind === 'save') {
        requestId.current ??= crypto.randomUUID()
        await saveHistory(result.parameters, requestId.current, current.signal)
        if (!current.signal.aborted) { setSaved(true); setMessage('Cálculo guardado en tu historial.') }
      } else {
        const file = await exportCalculation(result.parameters, kind, current.signal)
        if (!current.signal.aborted) { downloadFile(file, `newtonlab.${kind}`); setMessage(`Descarga ${kind.toUpperCase()} iniciada.`) }
      }
    } catch (error) {
      if (!current.signal.aborted) setMessage(error instanceof Error ? error.message : 'No se pudo completar la operación.')
    } finally {
      if (!current.signal.aborted) { setPending(null); controller.current = null }
    }
  }

  return <div className="space-y-2">
    <div className="flex flex-wrap gap-2" role="group" aria-label="Guardar y exportar">
      <Button variant="outline" size="sm" disabled={saved || Boolean(pending)} onClick={() => void act('save')}>{saved ? 'Guardado' : pending === 'save' ? 'Guardando…' : 'Guardar cálculo'}</Button>
      <Button variant="outline" size="sm" disabled={Boolean(pending)} onClick={() => void act('pdf')}>{pending === 'pdf' ? 'Generando PDF…' : 'Exportar PDF'}</Button>
      <Button variant="outline" size="sm" disabled={Boolean(pending) || result.iteration_count === 0} onClick={() => void act('csv')}>{pending === 'csv' ? 'Generando CSV…' : 'Exportar CSV'}</Button>
    </div>
    {message && <p role="status" className="text-sm text-muted-foreground">{message}</p>}
  </div>
}
