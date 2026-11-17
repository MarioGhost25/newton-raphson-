import { useEffect, useState } from 'react'
import { checkHealth } from '@/services/api'
import { Button } from '@/components/ui/button'

export function ConnectionStatus() {
  const [attempt, setAttempt] = useState(0)
  const [status, setStatus] = useState<'loading' | 'connected' | 'error'>('loading')
  useEffect(() => {
    const controller = new AbortController()
    setStatus('loading')
    void checkHealth(controller.signal)
      .then(() => { if (!controller.signal.aborted) setStatus('connected') })
      .catch(() => { if (!controller.signal.aborted) setStatus('error') })
    return () => controller.abort()
  }, [attempt])
  return <div className="flex items-center gap-2 text-xs text-muted-foreground">
    <span role="status">{status === 'loading' ? 'Conectando…' : status === 'connected' ? 'Servidor conectado' : 'Servidor no disponible'}</span>
    {status === 'error' && <Button variant="outline" size="sm" onClick={() => setAttempt(value => value + 1)}>Reintentar conexión</Button>}
  </div>
}
