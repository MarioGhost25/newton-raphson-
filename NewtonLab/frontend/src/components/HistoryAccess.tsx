import { lazy, Suspense, useRef, useState } from 'react'
import type { RestoredCalculation } from '@/types/history'
import { Button } from './ui/button'

const HistoryDialog = lazy(() => import('./HistoryDialog'))
export function HistoryAccess({ onRestore }: { onRestore: (result: RestoredCalculation) => void }) {
  const [open, setOpen] = useState(false)
  const button = useRef<HTMLButtonElement>(null)
  return <>
    <Button ref={button} size="sm" variant="outline" onClick={() => setOpen(true)}>Historial</Button>
    {open && <Suspense fallback={<span role="status" className="text-xs">Cargando historial…</span>}><HistoryDialog onRestore={onRestore} onClose={() => { setOpen(false); button.current?.focus() }} /></Suspense>}
  </>
}
