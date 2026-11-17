import type { CalculationResult } from '@/types/calculation'

export const result: CalculationResult = {
  expression: 'x - 1', derivative: '1',
  parameters: { expression: 'x - 1', initial_guess: 2, tolerance: 1e-6, max_iterations: 100 },
  root: 1, last_approximation: 1, converged: true, status: 'Convergencia alcanzada',
  termination_reason: 'Error y residuo cumplen la tolerancia.', final_residual: 0, final_error: 0,
  iteration_count: 2, iterations: [
    { index: 1, x: 2, fx: 1, derivative: 1, next_x: 1, absolute_error: 1, residual: 0 },
    { index: 2, x: 1, fx: 0, derivative: 1, next_x: 1, absolute_error: 0, residual: 0 },
  ], curve: { x: [0, 1, 2, 3], y: [-1, 0, 1, 2], notice: '' },
}
