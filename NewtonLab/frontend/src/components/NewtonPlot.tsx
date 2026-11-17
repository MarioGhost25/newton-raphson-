import { memo, useEffect, useMemo, useRef, useState } from 'react'
import Plotly from 'plotly.js-basic-dist-min'
import type { CalculationResult } from '@/types/calculation'
import { createPlot, type PlotColors } from '@/lib/plot'

const config: Partial<Plotly.Config> = { displaylogo: false, responsive: false, scrollZoom: false, displayModeBar: false }

function readColors(): PlotColors {
  const styles = getComputedStyle(document.documentElement)
  const color = (name: string) => styles.getPropertyValue(`--${name}`).trim()
  return { background: color('panel'), text: color('muted-foreground'), grid: color('border'), function: color('graph-function'), tangent: color('graph-tangent'), iteration: color('graph-iteration'), reference: color('graph-reference'), root: color('graph-root') }
}

export default memo(function NewtonPlot({ result, selected, revision }: { result: CalculationResult; selected: number; revision: number }) {
  const host = useRef<HTMLDivElement>(null)
  const controller = useRef<{ update: (spec: ReturnType<typeof createPlot>) => void } | null>(null)
  const [error, setError] = useState(false)
  const colors = useMemo(readColors, [])
  const spec = useMemo(() => createPlot(result, selected, colors, revision), [result, selected, colors, revision])
  useEffect(() => {
    if (!host.current) return
    const element = document.createElement('div')
    element.style.height = '100%'
    host.current.appendChild(element)
    let active = true
    let ready = false
    let sequence = Promise.resolve()
    let version = 0
    let frame = 0
    controller.current = { update(next) {
      const current = ++version
      sequence = sequence.then(async () => {
        if (!active || current !== version) return
        await Plotly.react(element, next.data, next.layout, config)
        ready = true
      }).catch(() => { if (active) setError(true) })
    } }
    const observer = new ResizeObserver(() => {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() => {
        if (active && ready) void Promise.resolve(Plotly.Plots.resize(element)).catch(() => { if (active) setError(true) })
      })
    })
    observer.observe(host.current)
    return () => {
      active = false; controller.current = null; observer.disconnect(); cancelAnimationFrame(frame)
      element.remove()
      // Espera operaciones en vuelo antes de liberar listeners y recursos de Plotly.
      void sequence.finally(() => Plotly.purge(element))
    }
  }, [])
  useEffect(() => { controller.current?.update(spec) }, [spec])
  return <div>
    {error && <p role="alert" className="p-4 text-sm">No se pudo dibujar la gráfica. Los resultados y la tabla siguen disponibles.</p>}
    <div ref={host} className="h-[340px] w-full sm:h-[410px]" role="img" aria-label={`Gráfica de ${result.expression}. ${result.iteration_count ? `Tangente de la iteración ${selected + 1}.` : 'Sin tangentes.'} Los valores están disponibles en la tabla de iteraciones.`} />
  </div>
})
