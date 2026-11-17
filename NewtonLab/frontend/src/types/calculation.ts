export interface CalculationRequest {
  expression: string
  initial_guess: number
  tolerance: number
  max_iterations: number
}

export interface Iteration {
  index: number
  x: number
  fx: number
  derivative: number
  next_x: number
  absolute_error: number
  residual: number
}

export const statuses = ['Convergencia alcanzada', 'Derivada nula o casi nula', 'Error de dominio', 'Valor no finito', 'Sin convergencia'] as const

export interface CalculationResult {
  expression: string
  derivative: string
  parameters: CalculationRequest
  root: number | null
  last_approximation: number
  converged: boolean
  status: typeof statuses[number]
  termination_reason: string
  final_residual: number | null
  final_error: number | null
  iteration_count: number
  iterations: Iteration[]
  curve: { x: number[]; y: (number | null)[]; notice: string }
}
