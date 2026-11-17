import { useEffect, useRef, useState } from 'react'
import type { HistoryPage, RestoredCalculation } from '@/types/history'
import { deleteHistory, listHistory, restoreHistory } from '@/services/history'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from './ui/dialog'

interface Props { onClose: () => void; onRestore: (restored: RestoredCalculation) => void }
export default function HistoryDialog({ onClose, onRestore }: Props) {
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('')
  const [offset, setOffset] = useState(0)
  const [reload, setReload] = useState(0)
  const [page, setPage] = useState<HistoryPage | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [confirm, setConfirm] = useState<string | null>(null)
  const operation = useRef<AbortController | null>(null)
  useEffect(() => () => operation.current?.abort(), [])

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setMessage(''); setPage(null)
    void listHistory(query, offset, controller.signal).then(data => {
      if (controller.signal.aborted) return
      if (!data.items.length && offset > 0) setOffset(value => Math.max(0, value - 20))
      else setPage(data)
    }).catch(error => {
      if (!controller.signal.aborted) setMessage(error instanceof Error ? error.message : 'No se pudo consultar el historial.')
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [query, offset, reload])

  async function perform(id: string, action: 'restore' | 'delete') {
    if (operation.current) return
    const controller = new AbortController(); operation.current = controller
    setBusy(true); setMessage('')
    try {
      if (action === 'restore') {
        const data = await restoreHistory(id, controller.signal)
        if (!controller.signal.aborted) { onRestore(data); onClose() }
      } else {
        await deleteHistory(id === 'all' ? null : id, controller.signal)
        if (!controller.signal.aborted) { setConfirm(null); setReload(value => value + 1) }
      }
    } catch (error) {
      if (!controller.signal.aborted) { setConfirm(null); setMessage(error instanceof Error ? error.message : 'No se pudo completar la operación.') }
    } finally {
      if (!controller.signal.aborted) { operation.current = null; setBusy(false) }
    }
  }

  return <Dialog open onOpenChange={open => { if (!open) onClose() }}>
    <DialogContent className="max-h-[85dvh] max-w-2xl overflow-y-auto">
      <DialogHeader><DialogTitle>Tu historial</DialogTitle><DialogDescription>Privado para este navegador. El identificador local no es una cuenta: perderlo o borrarlo impide recuperar el acceso; compartirlo expone tu historial.</DialogDescription></DialogHeader>
      <form className="flex gap-2" onSubmit={event => { event.preventDefault(); setOffset(0); setQuery(search); setReload(value => value + 1) }}>
        <Input aria-label="Buscar por expresión" value={search} maxLength={512} onChange={event => setSearch(event.target.value)} />
        <Button type="submit" variant="secondary" disabled={loading || busy}>Buscar</Button>
      </form>
      <p className="text-xs text-muted-foreground">Restaurar reconstruye la gráfica con el motor actual y selecciona el primer paso.</p>
      {message && <p role="alert" className="text-sm">{message}</p>}
      {loading && <p role="status" className="text-sm">Consultando historial…</p>}
      {busy && <p role="status" className="text-sm">Procesando…</p>}
      {page && <>
        {!page.items.length && <p className="text-sm text-muted-foreground">No hay cálculos para esta búsqueda.</p>}
        <ul className="space-y-2">{page.items.map(item => <li key={item.id} className="rounded border p-3">
          <p className="break-all font-mono text-sm">{item.summary.expression}</p>
          <p className="mt-1 text-xs text-muted-foreground">{new Date(item.created_at).toLocaleString()} · {item.summary.status} · {item.summary.iteration_count} pasos</p>
          <div className="mt-2 flex gap-2"><Button variant="secondary" size="sm" disabled={busy} onClick={() => void perform(item.id, 'restore')}>Restaurar</Button><Button variant="ghost" size="sm" disabled={busy} onClick={() => setConfirm(item.id)}>Eliminar</Button></div>
        </li>)}</ul>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <Button variant="outline" size="sm" disabled={busy || loading || offset === 0} onClick={() => setOffset(value => value - 20)}>Anterior</Button>
          <span className="text-xs">Página {offset / 20 + 1}</span>
          <Button variant="outline" size="sm" disabled={busy || loading || !page.has_more || offset >= 10000} onClick={() => setOffset(value => value + 20)}>Siguiente</Button>
          <Button variant="outline" size="sm" disabled={busy || loading} onClick={() => setConfirm('all')}>Vaciar mi historial</Button>
        </div>
      </>}
      <Dialog open={confirm !== null} onOpenChange={open => { if (!open && !busy) setConfirm(null) }}>
        <DialogContent><DialogHeader><DialogTitle>{confirm === 'all' ? '¿Vaciar tu historial?' : '¿Eliminar este cálculo?'}</DialogTitle><DialogDescription>Esta acción elimina los registros seleccionados de tu historial web y no se puede deshacer.</DialogDescription></DialogHeader>
          <div className="flex justify-end gap-2"><Button variant="outline" disabled={busy} onClick={() => setConfirm(null)}>Cancelar</Button><Button disabled={busy} onClick={() => { if (confirm) void perform(confirm, 'delete') }}>{busy ? 'Eliminando…' : 'Confirmar eliminación'}</Button></div>
        </DialogContent>
      </Dialog>
    </DialogContent>
  </Dialog>
}
