import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, renderHook } from '@testing-library/react'
import { useCalculation, validate, defaults } from '@/hooks/useCalculation'
import { usePlayback } from '@/hooks/usePlayback'
import { calculate } from '@/services/api'
import { result } from './fixture'

vi.mock('@/services/api', () => ({ calculate: vi.fn() }))
afterEach(() => { cleanup(); vi.useRealTimers() })

describe('solicitudes', () => {
  it('descarta respuestas anteriores al editar y aborta la solicitud', async () => {
    let finish!: (value: typeof result) => void
    vi.mocked(calculate).mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
    const hook = renderHook(useCalculation)
    let pending!: Promise<void>
    act(() => { pending = hook.result.current.submit() })
    const signal = vi.mocked(calculate).mock.calls[0]?.[1]
    act(() => hook.result.current.change('expression', 'cos(x)-x'))
    expect(signal?.aborted).toBe(true)
    await act(async () => { finish(result); await pending })
    expect(hook.result.current.result).toBeNull()
    expect(hook.result.current.fields.expression).toBe('cos(x)-x')
    expect(hook.result.current.pending).toBe(false)
  })

  it('presenta fallos y permite volver a calcular', async () => {
    vi.mocked(calculate).mockRejectedValueOnce(new Error('Servidor ocupado')).mockResolvedValueOnce(result)
    const hook = renderHook(useCalculation)
    await act(() => hook.result.current.submit())
    expect(hook.result.current.error).toBe('Servidor ocupado')
    await act(() => hook.result.current.submit())
    expect(hook.result.current.result).toEqual(result)
    expect(hook.result.current.error).toBeNull()
  })

  it('cancela al desmontar y no envía entradas inválidas', () => {
    vi.mocked(calculate).mockImplementationOnce(() => new Promise(() => {}))
    const hook = renderHook(useCalculation)
    act(() => { void hook.result.current.submit() })
    const signal = vi.mocked(calculate).mock.calls[0]?.[1]
    hook.unmount()
    expect(signal?.aborted).toBe(true)
    expect(validate({ ...defaults, initial_guess: '', tolerance: 'NaN', max_iterations: '201' }).errors).toHaveProperty('initial_guess')
    expect(Object.keys(validate({ ...defaults, initial_guess: '', tolerance: 'NaN', max_iterations: '201' }).errors)).toHaveLength(3)
  })
})

describe('reproducción', () => {
  it('avanza, pausa al seleccionar y libera timers al desmontar', () => {
    vi.useFakeTimers()
    const hook = renderHook(() => usePlayback(4))
    act(() => hook.result.current.toggle())
    act(() => vi.advanceTimersByTime(1000))
    expect(hook.result.current.selected).toBe(1)
    act(() => hook.result.current.select(2))
    expect(hook.result.current.playing).toBe(false)
    expect(vi.getTimerCount()).toBe(0)
    act(() => hook.result.current.toggle())
    hook.unmount()
    expect(vi.getTimerCount()).toBe(0)
  })
  it('termina en el último paso y no reproduce resultados sin pasos', () => {
    vi.useFakeTimers()
    const hook = renderHook(() => usePlayback(2))
    act(() => hook.result.current.toggle())
    act(() => vi.advanceTimersByTime(1000))
    expect(hook.result.current.selected).toBe(1)
    expect(hook.result.current.playing).toBe(false)
    act(() => hook.result.current.toggle())
    expect(hook.result.current.selected).toBe(0)
    const empty = renderHook(() => usePlayback(0))
    act(() => empty.result.current.toggle())
    expect(empty.result.current.playing).toBe(false)
  })
})
