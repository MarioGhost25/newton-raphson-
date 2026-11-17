import { memo, useEffect, useRef } from 'react'
import type { Iteration } from '@/types/calculation'
import { formatNumber } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableCaption } from '@/components/ui/table'

const IterationRow = memo(function IterationRow({ step, active, onSelect }: { step: Iteration; active: boolean; onSelect: (index: number) => void }) {
  return <TableRow data-state={active ? 'selected' : undefined} aria-current={active ? 'step' : undefined}>
    <TableCell><Button size="sm" variant={active ? 'secondary' : 'ghost'} aria-label={`Seleccionar iteración ${step.index}`} aria-pressed={active} onClick={() => onSelect(step.index - 1)}>{step.index}</Button></TableCell>
    {[step.x, step.fx, step.derivative, step.next_x, step.absolute_error].map((value, index) => <TableCell key={index} className="whitespace-nowrap font-mono text-xs tabular-nums" title={String(value)}>{formatNumber(value)}</TableCell>)}
  </TableRow>
})

export function IterationTable({ steps, selected, onSelect }: { steps: Iteration[]; selected: number; onSelect: (index: number) => void }) {
  const container = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const viewport = container.current?.firstElementChild
    const row = viewport?.querySelector<HTMLTableRowElement>('[aria-current="step"]')
    if (!(viewport instanceof HTMLElement) || !row) return
    const parent = viewport.getBoundingClientRect()
    const rect = row.getBoundingClientRect()
    // Sólo desplaza la tabla; no mueve la página ni roba el foco del teclado.
    if (rect.bottom > parent.bottom) viewport.scrollTop += rect.bottom - parent.bottom
    else if (rect.top < parent.top + 42) viewport.scrollTop -= parent.top + 42 - rect.top
  }, [selected])
  return <section className="panel min-w-0" aria-labelledby="iterations-title">
    <div className="flex items-center justify-between border-b px-5 py-4"><h2 id="iterations-title" className="font-medium">Iteraciones</h2><span className="text-xs text-muted-foreground">{steps.length} pasos completados</span></div>
    {steps.length ? <div ref={container} className="[&>div]:max-h-80">
      <Table>
        <TableCaption className="sr-only">Valores calculados en el servidor. Seleccioná un paso para ver su tangente.</TableCaption>
        <TableHeader className="sticky top-0 z-10 bg-panel"><TableRow>{['n', 'xₙ', 'f(xₙ)', 'f′(xₙ)', 'xₙ₊₁', 'Error absoluto'].map(label => <TableHead key={label} scope="col">{label}</TableHead>)}</TableRow></TableHeader>
        <TableBody>{steps.map(step => <IterationRow key={step.index} step={step} active={step.index === selected + 1} onSelect={onSelect} />)}</TableBody>
      </Table>
    </div> : <p className="p-5 text-sm text-muted-foreground">No se completaron iteraciones. Revisá el motivo de finalización.</p>}
  </section>
}
