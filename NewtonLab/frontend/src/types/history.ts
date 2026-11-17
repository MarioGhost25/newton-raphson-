import type { CalculationResult } from './calculation'

export type CalculationSummary = Omit<CalculationResult, 'iterations' | 'curve'>
export interface HistoryEntry { id: string; created_at: string; summary: CalculationSummary }
export interface HistoryPage { items: HistoryEntry[]; has_more: boolean; offset: number; limit: number }
export interface RestoredCalculation { entry: HistoryEntry; result: CalculationResult }
