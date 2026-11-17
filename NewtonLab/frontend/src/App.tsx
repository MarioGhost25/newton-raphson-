import { Activity } from 'lucide-react'
import { CalculationForm } from '@/components/CalculationForm'
import { ConnectionStatus } from '@/components/ConnectionStatus'
import { ResultSummary } from '@/components/ResultSummary'
import { CalculationWorkspace } from '@/components/CalculationWorkspace'
import { useCalculation } from '@/hooks/useCalculation'
import { HistoryAccess } from '@/components/HistoryAccess'
import { ExerciseLibrary } from '@/components/ExerciseLibrary'
import { CalculationActions } from '@/components/CalculationActions'

export default function App() {
  const calculation = useCalculation()
  return <div className="mx-auto max-w-[1600px] px-4 sm:px-7">
    <a href="#calculator" className="sr-only focus:not-sr-only focus:block focus:p-3">Ir al cálculo</a>
    <header className="flex flex-wrap items-center justify-between gap-3 border-b py-5">
      <div className="flex items-center gap-3"><Activity size={22} aria-hidden="true" /><span className="text-xl font-semibold tracking-tight">NewtonLab</span><span className="border-l pl-3 text-xs text-muted-foreground">WEB / 03</span></div>
      <div className="flex flex-wrap items-center gap-2"><ExerciseLibrary onLoad={calculation.load} /><HistoryAccess onRestore={data => calculation.load(data.result.parameters, data.result, data.entry.id)} /><ConnectionStatus /></div>
    </header>
    <main id="calculator" className="pb-8">
      <div className="py-7"><p className="mb-2 text-xs tracking-[.16em] text-muted-foreground">MÉTODOS NUMÉRICOS</p><h1 className="text-2xl font-medium tracking-tight">Newton-Raphson</h1><p className="mt-2 text-sm text-muted-foreground">De una aproximación inicial a una raíz, paso a paso.</p></div>
      <div className="grid items-start gap-5 lg:grid-cols-[300px_minmax(0,1fr)]">
        <CalculationForm fields={calculation.fields} errors={calculation.errors} pending={calculation.pending} onChange={calculation.change} onSubmit={calculation.submit} onReset={calculation.reset} onCancel={calculation.cancel} />
        <div className="min-w-0 space-y-5" aria-busy={calculation.pending}>
          {calculation.error && <div role="alert" className="panel p-5"><h2 className="mb-2 font-medium">No se pudo calcular</h2><p className="text-sm text-muted-foreground">{calculation.error}</p></div>}
          {calculation.result ? <><CalculationActions key={calculation.version} result={calculation.result} savedId={calculation.savedId} /><ResultSummary result={calculation.result} /><CalculationWorkspace key={calculation.version} result={calculation.result} /></> : <section className="panel flex min-h-[420px] flex-col items-center justify-center px-6 text-center" aria-label="Área de resultados">
            <span className="mb-6 font-mono text-xl text-muted-foreground" aria-hidden="true">xₙ₊₁ = xₙ − f(xₙ) / f′(xₙ)</span>
            <h2 className="font-medium" role="status">{calculation.pending ? 'Calculando en el servidor…' : 'Todo empieza con una función'}</h2>
            <p className="mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">{calculation.pending ? 'Podés cancelar la espera o editar los parámetros.' : 'Ingresá los parámetros y calculá para explorar la curva, las tangentes y cada iteración.'}</p>
          </section>}
        </div>
      </div>
    </main>
    <footer className="border-t py-5 text-xs text-muted-foreground">NewtonLab · Cálculo en números reales · Newton no garantiza convergencia</footer>
  </div>
}
