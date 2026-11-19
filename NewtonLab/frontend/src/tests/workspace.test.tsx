import { afterEach, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import Plotly from 'plotly.js-basic-dist-min'
import { CalculationWorkspace } from '@/components/CalculationWorkspace'
import { result } from './fixture'

vi.mock('plotly.js-basic-dist-min', () => ({ default: { react: vi.fn().mockResolvedValue(undefined), purge: vi.fn(), Plots: { resize: vi.fn() } } }))
afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals() })

it('sincroniza filas, controles y animación con los datos enviados a Plotly', async () => {
  vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} })
  render(<CalculationWorkspace result={result} />)
  await waitFor(() => expect(Plotly.react).toHaveBeenCalled())
  const check = (index: number) => {
    const call = vi.mocked(Plotly.react).mock.calls.at(-1)!
    expect(call[1]).toEqual(expect.arrayContaining([expect.objectContaining({ name: 'Paso seleccionado', x: [result.iterations[index]!.x] })]))
    expect(screen.getByRole('button', { name: `Seleccionar iteración ${index + 1}` }).getAttribute('aria-pressed')).toBe('true')
  }
  check(0)
  fireEvent.click(screen.getByRole('button', { name: 'Seleccionar iteración 2' }))
  await waitFor(() => check(1))
  fireEvent.click(screen.getByRole('button', { name: 'Primera iteración' }))
  await waitFor(() => check(0))
  vi.useFakeTimers()
  fireEvent.click(screen.getByRole('button', { name: 'Reproducir' }))
  await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
  check(1)
  expect(screen.getByRole('button', { name: 'Reproducir' }).getAttribute('aria-pressed')).toBe('false')
})
