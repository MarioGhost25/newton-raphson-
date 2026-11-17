import { afterEach, expect, it, vi } from 'vitest'
import { calculate, checkHealth, isCalculationResult } from '@/services/api'
import { createPlot, type PlotColors } from '@/lib/plot'
import { result } from './fixture'

afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers() })

it('valida números finitos, pasos y curva recibidos', () => {
  expect(isCalculationResult(result)).toBe(true)
  expect(isCalculationResult({ ...result, root: Infinity })).toBe(false)
  expect(isCalculationResult({ ...result, iterations: [{}] })).toBe(false)
  expect(isCalculationResult({ ...result, curve: { x: [0, 1], y: [0], notice: '' } })).toBe(false)
})

it('comunica errores HTTP y rechaza una respuesta sin contrato', async () => {
  const fetch = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ detail: 'Expresión inválida' }), { status: 422 }))
    .mockResolvedValueOnce(new Response('{}'))
  vi.stubGlobal('fetch', fetch)
  await expect(calculate(result.parameters, new AbortController().signal)).rejects.toThrow('Expresión inválida')
  await expect(calculate(result.parameters, new AbortController().signal)).rejects.toThrow('resultado inválido')
})

it('aborta la espera de health al vencer y limpia el timer', async () => {
  vi.useFakeTimers()
  vi.stubGlobal('fetch', vi.fn((_url: string, init: RequestInit) => new Promise((_resolve, reject) => {
    init.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
  })))
  const pending = expect(checkHealth(new AbortController().signal)).rejects.toThrow('no respondió a tiempo')
  await vi.advanceTimersByTimeAsync(5000)
  await pending
  expect(vi.getTimerCount()).toBe(0)
})

it('construye tangentes con datos del servidor sin modificar el resultado', () => {
  const colors = Object.fromEntries(['background', 'text', 'grid', 'function', 'tangent', 'iteration', 'reference', 'root'].map(key => [key, '#aaa'])) as unknown as PlotColors
  const original = structuredClone(result)
  const spec = createPlot(result, 0, colors, 0)
  expect(spec.data.find(trace => trace.name === 'Tangente n=1')).toMatchObject({ x: [0, 3], y: [-1, 2] })
  expect(result).toEqual(original)
  expect(createPlot({ ...result, root: null, converged: false }, 0, colors, 0).data.some(trace => trace.name === 'Raíz aproximada')).toBe(false)
})
