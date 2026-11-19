import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CalculationForm } from '@/components/CalculationForm'
import { IterationTable } from '@/components/IterationTable'
import { defaults } from '@/hooks/useCalculation'
import { result } from './fixture'

afterEach(cleanup)

it('muestra las columnas del cuaderno y conserva precisión y selección al desplegar', async () => {
  const step = { ...result.iterations[0]!, x: 1.23456789012345, next_x: 0.7071067811865476 }
  step.absolute_error = Math.abs(step.next_x - step.x)
  render(<IterationTable steps={[step]} selected={0} onSelect={vi.fn()} />)
  expect(screen.getAllByRole('columnheader').map(cell => cell.textContent)).toEqual(['It', 'xᵢ', 'xᵢ₊₁', 'Error'])
  const row = screen.getAllByRole('row')[1]!
  expect(within(row).getAllByRole('cell').slice(1).map(cell => cell.title)).toEqual([step.x, step.next_x, step.absolute_error].map(String))
  await userEvent.click(screen.getByRole('button', { name: 'Mostrar detalle' }))
  expect(screen.getAllByRole('columnheader').map(cell => cell.textContent)).toEqual(['It', 'xᵢ', 'xᵢ₊₁', 'Error', 'f(xᵢ)', 'f′(xᵢ)'])
  expect(row.getAttribute('aria-current')).toBe('step')
})

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
