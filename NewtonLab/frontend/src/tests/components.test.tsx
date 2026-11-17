import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CalculationForm } from '@/components/CalculationForm'
import { IterationTable } from '@/components/IterationTable'
import { defaults } from '@/hooks/useCalculation'
import { result } from './fixture'

afterEach(cleanup)

it('asocia etiquetas y enfoca el primer campo inválido', async () => {
  const submit = vi.fn(async () => {})
  render(<CalculationForm fields={{ ...defaults, initial_guess: '' }} errors={{ initial_guess: 'Valor requerido' }} pending={false} onChange={vi.fn()} onSubmit={submit} onReset={vi.fn()} onCancel={vi.fn()} />)
  await userEvent.click(screen.getByRole('button', { name: 'Calcular raíz' }))
  expect(document.activeElement).toBe(screen.getByLabelText('Valor inicial x₀'))
  expect(document.activeElement?.getAttribute('aria-invalid')).toBe('true')
})

it('permite seleccionar una iteración por teclado', async () => {
  const select = vi.fn()
  render(<IterationTable steps={result.iterations} selected={0} onSelect={select} />)
  const button = screen.getByRole('button', { name: 'Seleccionar iteración 2' })
  button.focus()
  await userEvent.keyboard('{Enter}')
  expect(select).toHaveBeenCalledWith(1)
})

it('el diálogo de sintaxis devuelve el foco al cerrarse con Escape', async () => {
  render(<CalculationForm fields={defaults} errors={{}} pending={false} onChange={vi.fn()} onSubmit={vi.fn(async () => {})} onReset={vi.fn()} onCancel={vi.fn()} />)
  const trigger = screen.getByRole('button', { name: 'Sintaxis' })
  await userEvent.click(trigger)
  expect(screen.getByRole('dialog')).toBeTruthy()
  await userEvent.keyboard('{Escape}')
  expect(screen.queryByRole('dialog')).toBeNull()
  expect(document.activeElement).toBe(trigger)
})
