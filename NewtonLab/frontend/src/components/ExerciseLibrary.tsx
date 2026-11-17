import { useState } from 'react'
import { exercises } from '@/data/exercises'
import type { CalculationRequest } from '@/types/calculation'
import { Button } from './ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog'

export function ExerciseLibrary({ onLoad }: { onLoad: (parameters: CalculationRequest) => void }) {
  const [open, setOpen] = useState(false)
  return <Dialog open={open} onOpenChange={setOpen}>
    <DialogTrigger asChild><Button variant="outline" size="sm">Ejercicios</Button></DialogTrigger>
    <DialogContent className="max-h-[85dvh] overflow-y-auto">
      <DialogHeader><DialogTitle>Biblioteca de ejercicios</DialogTitle><DialogDescription>Cargá los parámetros sugeridos. Podés modificarlos antes de calcular.</DialogDescription></DialogHeader>
      <ul className="space-y-3">{exercises.map(exercise => <li key={exercise.id} className="rounded border p-3">
        <p className="text-xs text-muted-foreground">{exercise.category}</p><h3 className="my-1 text-sm font-medium">{exercise.title}</h3>
        <code className="text-xs">{exercise.expression}</code><p className="my-2 text-xs text-muted-foreground">{exercise.description}</p>
        <Button variant="secondary" size="sm" onClick={() => { onLoad(exercise); setOpen(false) }} aria-label={`Cargar ${exercise.title}`}>Cargar parámetros</Button>
      </li>)}</ul>
    </DialogContent>
  </Dialog>
}
