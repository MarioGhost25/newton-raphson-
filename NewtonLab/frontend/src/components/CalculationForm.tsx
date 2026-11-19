import { useRef, type FormEvent } from 'react'
import { Calculator, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { validate, type Fields, type FieldErrors } from '@/hooks/useCalculation'

interface Props {
  fields: Fields; errors: FieldErrors; pending: boolean
  onChange: (key: keyof Fields, value: string) => void
  onSubmit: () => Promise<void>; onReset: () => void; onCancel: () => void
}
const inputs = [
  { key: 'expression', label: 'Función f(x)', hint: 'Ejemplo: 2x³ + 6x² − 8x + 2. Potencias: ², ^ o **.' },
  { key: 'initial_guess', label: 'Valor inicial x₀', hint: 'Punto de partida del método.' },
  { key: 'tolerance', label: 'Tolerancia', hint: 'Error absoluto y residuo, entre 1e-14 y 1.' },
  { key: 'max_iterations', label: 'Máximo de iteraciones', hint: 'Entre 1 y 200 pasos.' },
] as const

export function CalculationForm({ fields, errors, pending, onChange, onSubmit, onReset, onCancel }: Props) {
  const form = useRef<HTMLFormElement>(null)
  function submit(event: FormEvent) {
    event.preventDefault()
    const invalid = Object.keys(validate(fields).errors)[0]
    void onSubmit()
    if (invalid) form.current?.querySelector<HTMLInputElement>(`#${invalid}`)?.focus()
  }
  return <section className="panel p-5" aria-labelledby="parameters-title">
    <div className="mb-6 flex items-center justify-between">
      <h2 id="parameters-title" className="font-medium">Parámetros</h2>
      <Dialog>
        <DialogTrigger asChild><Button variant="ghost" size="sm">Sintaxis</Button></DialogTrigger>
        <DialogContent className="max-h-[85dvh] overflow-y-auto">
          <DialogHeader><DialogTitle>Escribí una función de x</DialogTitle><DialogDescription>El cálculo y la derivada se realizan en el servidor, usando números reales.</DialogDescription></DialogHeader>
          <div className="space-y-3 text-sm leading-relaxed text-muted-foreground">
            <p>Operadores: <code>+ − * / ^ **</code> y exponentes como <code>², ³</code>. Constantes: <code>pi, e, E</code>. Usá punto decimal. Podés escribir <code>2x</code>; para otros productos usá <code>*</code>.</p>
            <p>Funciones: <code>sin, cos, tan, asin, acos, atan, sinh, cosh, tanh, exp, log, sqrt, abs</code>. Todas reciben un argumento; los ángulos se expresan en radianes.</p>
            <p>Ejemplos: <code>x² - 0.5</code>, <code>x^3 - x - 2</code>, <code>cos(x) - x</code>.</p>
            <p>Newton no garantiza convergencia. Una derivada casi nula o un punto fuera del dominio puede detener el cálculo.</p>
          </div>
        </DialogContent>
      </Dialog>
    </div>
    <form ref={form} onSubmit={submit} noValidate className="space-y-5">
      {inputs.map(({ key, label, hint }) => <div key={key} className="space-y-2">
        <label htmlFor={key} className="text-sm font-medium">{label}</label>
        <Input id={key} name={key} value={fields[key]} onChange={event => onChange(key, event.target.value)}
          type="text" inputMode={key === 'expression' ? 'text' : key === 'max_iterations' ? 'numeric' : 'decimal'}
          maxLength={key === 'expression' ? 512 : 32} autoComplete="off" spellCheck={false}
          className="bg-control font-mono" aria-invalid={Boolean(errors[key])}
          aria-describedby={`${key}-hint${errors[key] ? ` ${key}-error` : ''}`} />
        <p id={`${key}-hint`} className="text-xs text-muted-foreground">{hint}</p>
        {errors[key] && <p id={`${key}-error`} className="text-xs font-medium" role="alert">{errors[key]}</p>}
      </div>)}
      <Button type="submit" disabled={pending} className="w-full"><Calculator aria-hidden="true" />{pending ? 'Calculando…' : 'Calcular raíz'}</Button>
      <div className="flex gap-2">
        <Button type="button" variant="outline" onClick={onReset} className="flex-1"><RotateCcw aria-hidden="true" />Restablecer</Button>
        {pending && <Button type="button" variant="outline" onClick={onCancel}>Cancelar</Button>}
      </div>
    </form>
  </section>
}
