import { afterEach, expect, it, vi } from 'vitest'
import { act, cleanup, render, renderHook, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ExerciseLibrary } from '@/components/ExerciseLibrary'
import { exercises } from '@/data/exercises'
import { useCalculation } from '@/hooks/useCalculation'
import { historyToken, listHistory, saveHistory } from '@/services/history'
import { downloadFile, exportCalculation } from '@/services/exports'
import { result } from './fixture'

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.useRealTimers(); localStorage.clear() })

it('la biblioteca carga parámetros editables sin solicitar cálculos', async () => {
  const fetch = vi.fn(); vi.stubGlobal('fetch', fetch)
  const load = vi.fn()
  render(<ExerciseLibrary onLoad={load} />)
  await userEvent.click(screen.getByRole('button', { name: 'Ejercicios' }))
  expect(exercises).toHaveLength(8)
  await userEvent.click(screen.getByRole('button', { name: 'Cargar Logaritmo natural' }))
  expect(load).toHaveBeenCalledWith(expect.objectContaining({ expression: 'log(x) - 1', initial_guess: 2 }))
  expect(fetch).not.toHaveBeenCalled()
})

it('restaurar actualiza parámetros, resultado y versión sin un segundo cálculo', () => {
  const fetch = vi.fn(); vi.stubGlobal('fetch', fetch)
  const hook = renderHook(useCalculation)
  act(() => hook.result.current.load(result.parameters, result, 'saved-id'))
  expect(hook.result.current.result).toEqual(result)
  expect(hook.result.current.fields.expression).toBe(result.expression)
  expect(hook.result.current.savedId).toBe('saved-id')
  expect(hook.result.current.version).toBe(1)
  act(() => hook.result.current.change('initial_guess', '3'))
  expect(hook.result.current.result).toBeNull()
  expect(hook.result.current.savedId).toBeNull()
  expect(fetch).not.toHaveBeenCalled()
})

it('el identificador tiene 256 bits y persiste sin formar parte de la URL', async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [], has_more: false, offset: 0, limit: 20 })))
  vi.stubGlobal('fetch', fetch)
  const token = historyToken()
  expect(token).toMatch(/^[a-f0-9]{64}$/)
  expect(historyToken()).toBe(token)
  await listHistory('x**2', 0, new AbortController().signal)
  expect(fetch.mock.calls[0]?.[0]).not.toContain(token)
  expect(fetch.mock.calls[0]?.[1].headers['X-History-Token']).toBe(token)
})

it('no usa un token efímero si el almacenamiento está bloqueado', () => {
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('blocked') })
  expect(historyToken).toThrow('almacenamiento local')
})

it('guardar envía parámetros e idempotencia, nunca resultados del cliente', async () => {
  const { iterations: _iterations, curve: _curve, ...summary } = result
  const entry = { id: crypto.randomUUID(), created_at: new Date().toISOString(), summary }
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(entry)))
  vi.stubGlobal('fetch', fetch)
  const requestId = crypto.randomUUID()
  await saveHistory(result.parameters, requestId, new AbortController().signal)
  expect(JSON.parse(fetch.mock.calls[0]?.[1].body)).toEqual({ request_id: requestId, parameters: result.parameters })
})

it('descarga el blob del servidor y libera la URL temporal', async () => {
  const blob = new Blob(['\ufeffIteración,x_n\n1,2'], { type: 'text/csv' })
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, blob: async () => blob }))
  const file = await exportCalculation(result.parameters, 'csv', new AbortController().signal)
  expect(file).toBe(blob)
  const create = vi.fn(() => 'blob:newtonlab')
  const revoke = vi.fn()
  vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: create, revokeObjectURL: revoke }))
  const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
  vi.useFakeTimers()
  downloadFile(file, 'newtonlab.csv')
  expect(click).toHaveBeenCalledOnce()
  expect(document.querySelector('a[download]')).toBeNull()
  vi.runAllTimers()
  expect(revoke).toHaveBeenCalledWith('blob:newtonlab')
})
