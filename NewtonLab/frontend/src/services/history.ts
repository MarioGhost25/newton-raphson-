import { request, isCalculationResult } from './api'
import { statuses, type CalculationRequest } from '@/types/calculation'
import type { HistoryEntry, HistoryPage, RestoredCalculation } from '@/types/history'

const STORAGE_KEY = 'newtonlab.history.token'
export function historyToken(): string {
  try {
    const existing = localStorage.getItem(STORAGE_KEY)
    if (existing && /^[a-f0-9]{64}$/.test(existing)) return existing
    const token = Array.from(crypto.getRandomValues(new Uint8Array(32)), byte => byte.toString(16).padStart(2, '0')).join('')
    localStorage.setItem(STORAGE_KEY, token)
    return token
  } catch {
    throw new Error('El historial requiere almacenamiento local del navegador. Habilitalo para continuar.')
  }
}

const record = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null
const finite = (value: unknown) => typeof value === 'number' && Number.isFinite(value)
const optionalNumber = (value: unknown) => value === null || finite(value)

export function isHistoryEntry(value: unknown): value is HistoryEntry {
  if (!record(value) || typeof value.id !== 'string' || !/^[\da-f-]{36}$/i.test(value.id)
    || typeof value.created_at !== 'string' || !Number.isFinite(Date.parse(value.created_at)) || !record(value.summary)) return false
  const s = value.summary
  const p = s.parameters
  return record(p) && typeof p.expression === 'string' && finite(p.initial_guess) && finite(p.tolerance) && Number.isInteger(p.max_iterations)
    && typeof s.expression === 'string' && typeof s.derivative === 'string' && finite(s.last_approximation)
    && optionalNumber(s.root) && optionalNumber(s.final_residual) && optionalNumber(s.final_error)
    && typeof s.converged === 'boolean' && statuses.some(status => status === s.status)
    && typeof s.termination_reason === 'string' && typeof s.iteration_count === 'number'
    && Number.isInteger(s.iteration_count) && s.iteration_count >= 0 && s.iteration_count <= 200
}

function headers(): HeadersInit { return { 'X-History-Token': historyToken(), 'Content-Type': 'application/json' } }

export async function listHistory(query: string, offset: number, signal: AbortSignal): Promise<HistoryPage> {
  const data = await request(`history?${new URLSearchParams({ q: query, offset: String(offset), limit: '20' })}`, signal, { headers: headers() })
  if (!record(data) || !Array.isArray(data.items) || !data.items.every(isHistoryEntry)
    || typeof data.has_more !== 'boolean' || data.offset !== offset || data.limit !== 20) throw new Error('Respuesta de historial inválida.')
  return { items: data.items, has_more: data.has_more, offset, limit: 20 }
}

export async function saveHistory(parameters: CalculationRequest, requestId: string, signal: AbortSignal): Promise<HistoryEntry> {
  const data = await request('history', signal, { method: 'POST', headers: headers(), body: JSON.stringify({ request_id: requestId, parameters }) })
  if (!isHistoryEntry(data)) throw new Error('No se pudo verificar el guardado.')
  return data
}

export async function restoreHistory(id: string, signal: AbortSignal): Promise<RestoredCalculation> {
  const data = await request(`history/${encodeURIComponent(id)}`, signal, { headers: headers() })
  if (!record(data) || !isHistoryEntry(data.entry) || !isCalculationResult(data.result)) throw new Error('No se pudo validar el cálculo restaurado.')
  return { entry: data.entry, result: data.result }
}

export async function deleteHistory(id: string | null, signal: AbortSignal): Promise<void> {
  await request(id ? `history/${encodeURIComponent(id)}` : 'history', signal, { method: 'DELETE', headers: headers() })
}
