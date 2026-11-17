import { memo } from 'react'
import type { CalculationResult } from '@/types/calculation'
import { formatNumber } from '@/lib/utils'

export const ResultSummary = memo(function ResultSummary({ result }: { result: CalculationResult }) {
  const metrics: [string, number | null][] = [
    [result.converged ? 'Raíz aproximada' : 'Última aproximación', result.converged ? result.root : result.last_approximation],
    ['Residuo final', result.final_residual], ['Error absoluto final', result.final_error], ['Iteraciones', result.iteration_count],
  ]
  return <section className="panel p-5" aria-labelledby="result-title">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h2 id="result-title" className="font-medium">Resultado</h2>
      <span className="rounded border px-2 py-1 text-xs">{result.status}</span>
    </div>
    <p className="mt-3 text-sm text-muted-foreground" role="status">{result.termination_reason}</p>
    <dl className="mt-5 grid grid-cols-2 gap-5 lg:grid-cols-4">
      {metrics.map(([label, value]) => <div key={label} className="min-w-0"><dt className="text-xs text-muted-foreground">{label}</dt><dd className="mt-1 break-all font-mono text-sm" title={String(value ?? 'Sin pasos completados')}>{formatNumber(value)}</dd></div>)}
    </dl>
    <p className="mt-5 break-all border-t pt-3 font-mono text-xs text-muted-foreground">f′(x) = {result.derivative}</p>
  </section>
})
