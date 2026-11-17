import { lazy, Suspense, useState } from 'react'
import { ChevronFirst, ChevronLast, ChevronLeft, ChevronRight, Pause, Play } from 'lucide-react'
import type { CalculationResult } from '@/types/calculation'
import { usePlayback } from '@/hooks/usePlayback'
import { formatNumber } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { IterationTable } from '@/components/IterationTable'
import { PlotBoundary } from '@/components/PlotBoundary'

const NewtonPlot = lazy(() => import('@/components/NewtonPlot'))

export function CalculationWorkspace({ result }: { result: CalculationResult }) {
  const playback = usePlayback(result.iteration_count)
  const [revision, setRevision] = useState(0)
  const step = result.iterations[playback.selected]
  const first = !step || playback.selected === 0
  const last = !step || playback.selected === result.iteration_count - 1
  return <>
    <section className="panel min-w-0" aria-labelledby="graph-title">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b px-5 py-3"><h2 id="graph-title" className="font-medium">Recorrido de Newton</h2><Button variant="outline" size="sm" onClick={() => setRevision(value => value + 1)}>Restaurar vista</Button></div>
      <div className="flex flex-wrap gap-x-5 gap-y-2 px-5 pt-4 text-xs text-muted-foreground">
        {([['function', 'Función'], ['tangent', 'Tangente'], ['iteration', 'Iteraciones'], ['reference', 'Intersección'], ['root', 'Raíz']] as const).map(([color, name]) => <span key={color} className="inline-flex items-center gap-2"><span aria-hidden="true" className="h-0.5 w-3" style={{ backgroundColor: `var(--graph-${color})` }} />{name}</span>)}
      </div>
      <PlotBoundary><Suspense fallback={<p role="status" className="flex h-[340px] items-center justify-center text-sm text-muted-foreground sm:h-[410px]">Cargando gráfica…</p>}><NewtonPlot result={result} selected={playback.selected} revision={revision} /></Suspense></PlotBoundary>
      <div className="space-y-3 border-t p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-1" role="group" aria-label="Recorrido de iteraciones">
            <Button variant="outline" size="icon" aria-label="Primera iteración" disabled={first} onClick={() => playback.select(0)}><ChevronFirst aria-hidden="true" /></Button>
            <Button variant="outline" size="icon" aria-label="Iteración anterior" disabled={first} onClick={() => playback.select(playback.selected - 1)}><ChevronLeft aria-hidden="true" /></Button>
            <Button variant="secondary" disabled={result.iteration_count < 2} aria-pressed={playback.playing} onClick={playback.toggle}>{playback.playing ? <Pause aria-hidden="true" /> : <Play aria-hidden="true" />}{playback.playing ? 'Pausar' : 'Reproducir'}</Button>
            <Button variant="outline" size="icon" aria-label="Iteración siguiente" disabled={last} onClick={() => playback.select(playback.selected + 1)}><ChevronRight aria-hidden="true" /></Button>
            <Button variant="outline" size="icon" aria-label="Última iteración" disabled={last} onClick={() => playback.select(result.iteration_count - 1)}><ChevronLast aria-hidden="true" /></Button>
          </div>
          <div className="flex gap-1" role="group" aria-label="Velocidad de reproducción">{([[1600, 'Lenta'], [1000, 'Normal'], [500, 'Rápida']] as const).map(([delay, label]) => <Button key={delay} variant={playback.delay === delay ? 'secondary' : 'ghost'} size="sm" aria-pressed={playback.delay === delay} onClick={() => playback.setDelay(delay)}>{label}</Button>)}</div>
        </div>
        <p className="break-words font-mono text-xs" aria-live={playback.playing ? 'off' : 'polite'}>{step ? `Paso ${step.index} de ${result.iteration_count} · xₙ₊₁ = ${formatNumber(step.x)} − (${formatNumber(step.fx)}) / (${formatNumber(step.derivative)}) = ${formatNumber(step.next_x)}` : 'No hay una tangente disponible: no se completaron pasos.'}</p>
        <p className="text-xs text-muted-foreground">Arrastrá un rectángulo para ampliar; doble clic para restaurar. La curva usa el muestreo del servidor, sin recalcular al ampliar.</p>
        {result.curve.notice && <p className="text-xs text-muted-foreground">{result.curve.notice}</p>}
      </div>
    </section>
    <IterationTable steps={result.iterations} selected={playback.selected} onSelect={playback.select} />
  </>
}
