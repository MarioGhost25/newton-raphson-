import { useCallback, useEffect, useRef, useState } from 'react'
import { calculate } from '@/services/api'
import { normalizeExpression } from '@/lib/expression'
import type { CalculationRequest, CalculationResult } from '@/types/calculation'

export type Fields = { [K in keyof CalculationRequest]: string }
export type FieldErrors = Partial<Record<keyof Fields, string>>
export const defaults: Fields = { expression: 'x**3 - x - 2', initial_guess: '1.5', tolerance: '0.000001', max_iterations: '100' }

export function validate(fields: Fields): { errors: FieldErrors; request: CalculationRequest } {
  const request = { expression: fields.expression.trim(), initial_guess: Number(fields.initial_guess), tolerance: Number(fields.tolerance), max_iterations: Number(fields.max_iterations) }
  const errors: FieldErrors = {}
  if (!request.expression || request.expression.length > 512) errors.expression = 'Introducí una función de hasta 512 caracteres.'
  else {
    try { request.expression = normalizeExpression(fields.expression) }
    catch (error) { errors.expression = (error as Error).message }
  }
  if (!fields.initial_guess.trim() || !Number.isFinite(request.initial_guess) || Math.abs(request.initial_guess) > 1e12) errors.initial_guess = 'Usá un número finito entre −1e12 y 1e12.'
  if (!Number.isFinite(request.tolerance) || request.tolerance < 1e-14 || request.tolerance > 1) errors.tolerance = 'La tolerancia debe estar entre 1e-14 y 1.'
  if (!Number.isInteger(request.max_iterations) || request.max_iterations < 1 || request.max_iterations > 200) errors.max_iterations = 'Usá un entero entre 1 y 200.'
  return { errors, request }
}

export function useCalculation() {
  const [fields, setFields] = useState<Fields>(defaults)
  const [errors, setErrors] = useState<FieldErrors>({})
  const [result, setResult] = useState<CalculationResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)
  const [savedId, setSavedId] = useState<string | null>(null)
  const [version, setVersion] = useState(0)
  const current = useRef<AbortController | null>(null)

  useEffect(() => () => current.current?.abort(), [])

  const cancel = useCallback(() => {
    current.current?.abort()
    current.current = null
    setPending(false)
  }, [])

  const change = useCallback((key: keyof Fields, value: string) => {
    cancel()
    setFields(previous => ({ ...previous, [key]: value }))
    setErrors({}); setError(null); setResult(null); setSavedId(null)
  }, [cancel])

  const reset = useCallback(() => {
    cancel(); setFields(defaults); setErrors({}); setError(null); setResult(null); setSavedId(null)
  }, [cancel])

  const load = useCallback((parameters: CalculationRequest, restored: CalculationResult | null = null, id: string | null = null) => {
    cancel()
    setFields({ expression: parameters.expression, initial_guess: String(parameters.initial_guess), tolerance: String(parameters.tolerance), max_iterations: String(parameters.max_iterations) })
    setErrors({}); setError(null); setResult(restored); setSavedId(id); setVersion(value => value + 1)
  }, [cancel])

  async function submit() {
    cancel()
    const validation = validate(fields)
    setErrors(validation.errors); setError(null); setResult(null); setSavedId(null)
    if (Object.keys(validation.errors).length) return
    const controller = new AbortController()
    current.current = controller
    setPending(true)
    try {
      const next = await calculate(validation.request, controller.signal)
      if (!controller.signal.aborted && current.current === controller) setResult(next)
    } catch (failure) {
      if (!controller.signal.aborted && current.current === controller) setError(failure instanceof Error ? failure.message : 'No se pudo completar el cálculo.')
    } finally {
      if (current.current === controller) { current.current = null; setPending(false) }
    }
  }

  return { fields, errors, result, error, pending, change, reset, cancel, submit, load, savedId, version }
}
