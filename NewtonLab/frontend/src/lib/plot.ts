import type { Data, Layout } from 'plotly.js'
import type { CalculationResult } from '@/types/calculation'

export interface PlotColors { background: string; text: string; grid: string; function: string; tangent: string; iteration: string; reference: string; root: string }

export function createPlot(result: CalculationResult, selected: number, colors: PlotColors, revision: number): { data: Data[]; layout: Partial<Layout> } {
  const { x, y } = result.curve
  const low = x[0] ?? -1
  const high = x[x.length - 1] ?? 1
  const data: Data[] = [{
    type: 'scatter', mode: 'lines', name: 'f(x)', x: [...x], y: [...y],
    line: { color: colors.function, width: 2 }, connectgaps: false,
    hovertemplate: 'x = %{x:.8g}<br>f(x) = %{y:.8g}<extra>Función</extra>',
  }, {
    type: 'scatter', mode: 'markers', name: 'Iteraciones',
    x: result.iterations.map(step => step.x), y: result.iterations.map(step => step.fx),
    marker: { color: colors.iteration, size: 6 },
    hovertemplate: 'xₙ = %{x:.8g}<br>f(xₙ) = %{y:.8g}<extra>Iteración</extra>',
  }]
  const step = result.iterations[selected]
  if (step) {
    const tangent = [low, high].map(value => step.fx + step.derivative * (value - step.x))
    data.push({ type: 'scatter', mode: 'lines', name: `Tangente n=${step.index}`, x: [low, high],
      y: tangent.map(value => Number.isFinite(value) ? value : null), line: { color: colors.tangent, width: 1.5 },
      hovertemplate: 'x = %{x:.8g}<br>y = %{y:.8g}<extra>Tangente</extra>' },
    { type: 'scatter', mode: 'markers', name: 'Paso seleccionado', x: [step.x], y: [step.fx], marker: { color: colors.iteration, size: 10, line: { color: colors.text, width: 1 } } },
    { type: 'scatter', mode: 'markers', name: 'Intersección xₙ₊₁', x: [step.next_x], y: [0], marker: { color: colors.reference, symbol: 'diamond', size: 9 } })
  }
  if (result.converged && result.root !== null) data.push({ type: 'scatter', mode: 'markers', name: 'Raíz aproximada', x: [result.root], y: [0], marker: { color: colors.root, size: 12, symbol: 'circle-open', line: { width: 2 } } })
  const finite = y.filter((value): value is number => value !== null && Number.isFinite(value)).sort((a, b) => a - b)
  const bottom = Math.min(0, finite[Math.floor(finite.length * .02)] ?? -1)
  const top = Math.max(0, finite[Math.min(finite.length - 1, Math.floor(finite.length * .98))] ?? 1)
  const margin = Math.max((top - bottom) * .12, 1e-6)
  return { data, layout: {
    autosize: true, paper_bgcolor: colors.background, plot_bgcolor: colors.background,
    font: { family: 'Segoe UI, sans-serif', color: colors.text, size: 11 },
    margin: { l: 65, r: 20, t: 20, b: 55 }, showlegend: false,
    xaxis: { title: { text: 'x' }, range: [low, high], gridcolor: colors.grid, zerolinecolor: colors.grid },
    yaxis: { title: { text: 'f(x)' }, range: [bottom - margin, top + margin], gridcolor: colors.grid, zerolinecolor: colors.grid },
    hovermode: 'closest', dragmode: 'zoom', uirevision: revision,
  } }
}
