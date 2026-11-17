import { statuses, type CalculationRequest, type CalculationResult } from '@/types/calculation'
import { apiUrl } from './apiUrl'

const record = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value)
const nullable = (value: unknown) => value === null || finite(value)

// Validación de la frontera HTTP: TypeScript no valida el JSON recibido.
export function isCalculationResult(value: unknown): value is CalculationResult {
  if (!record(value) || !record(value.parameters) || !record(value.curve)) return false
  const p = value.parameters
  return typeof value.expression === 'string' && typeof value.derivative === 'string'
    && typeof p.expression === 'string' && finite(p.initial_guess) && finite(p.tolerance) && Number.isInteger(p.max_iterations)
    && nullable(value.root) && finite(value.last_approximation) && typeof value.converged === 'boolean'
    && statuses.some(status => status === value.status) && typeof value.termination_reason === 'string'
    && nullable(value.final_residual) && nullable(value.final_error)
    && Array.isArray(value.iterations) && value.iterations.length <= 200
    && value.iteration_count === value.iterations.length
    && value.iterations.every((step: unknown, index: number) => record(step) && step.index === index + 1
      && ['x', 'fx', 'derivative', 'next_x', 'absolute_error', 'residual'].every(key => finite(step[key])))
    && Array.isArray(value.curve.x) && Array.isArray(value.curve.y)
    && value.curve.x.length > 1 && value.curve.x.length <= 5000
    && value.curve.x.length === value.curve.y.length
    && value.curve.x.every(finite) && value.curve.y.every(nullable) && typeof value.curve.notice === 'string'
}

export async function request(path: string, signal: AbortSignal, options: RequestInit = {}, timeout = 35000, format: 'json' | 'blob' = 'json'): Promise<unknown> {
  const controller = new AbortController()
  const abort = () => controller.abort()
  signal.addEventListener('abort', abort, { once: true })
  if (signal.aborted) controller.abort()
  const timer = window.setTimeout(abort, timeout)
  try {
    const response = await fetch(apiUrl(path), { ...options, signal: controller.signal, cache: 'no-store', credentials: 'omit' })
    const data: unknown = response.ok && format === 'blob' ? await response.blob() : await response.json().catch(() => null)
    if (!response.ok) {
      const detail = record(data) && typeof data.detail === 'string' ? data.detail : `Error del servidor (${response.status}).`
      throw new Error(detail)
    }
    return data
  } catch (error) {
    if (signal.aborted) throw error
    if (controller.signal.aborted) throw new Error('El servidor no respondió a tiempo. Intentá nuevamente.')
    if (error instanceof TypeError) throw new Error('No se pudo conectar con el servidor. Verificá la conexión.')
    throw error
  } finally {
    window.clearTimeout(timer)
    signal.removeEventListener('abort', abort)
  }
}

export async function checkHealth(signal: AbortSignal): Promise<void> {
  const data = await request('health', signal, {}, 5000)
  if (!record(data) || data.status !== 'ok' || data.service !== 'NewtonLab API') throw new Error('Servicio no disponible.')
}

export async function calculate(parameters: CalculationRequest, signal: AbortSignal): Promise<CalculationResult> {
  const data = await request('calculations/newton-raphson', signal, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(parameters),
  })
  if (!isCalculationResult(data)) throw new Error('El servidor devolvió un resultado inválido.')
  return data
}
