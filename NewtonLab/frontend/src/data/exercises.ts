import type { CalculationRequest } from '@/types/calculation'

export interface Exercise extends CalculationRequest { id: string; title: string; description: string; category: string }
// Mismos ejercicios académicos de app/data/examples.py; sin persistencia.
const common = { tolerance: 1e-8, max_iterations: 100 }
export const exercises: readonly Exercise[] = [
  { ...common, id: 'sqrt-two', title: 'Raíz cuadrada de dos', expression: 'x**2 - 2', initial_guess: 1.5, description: 'Convergencia hacia la raíz positiva de un polinomio cuadrático.', category: 'Polinómica' },
  { ...common, id: 'cubic', title: 'Polinomio cúbico', expression: 'x**3 - x - 2', initial_guess: 1.5, description: 'Construcción geométrica de las tangentes en una función cúbica.', category: 'Polinómica' },
  { ...common, id: 'cosine', title: 'Intersección con el coseno', expression: 'cos(x) - x', initial_guess: 1, description: 'Ecuación trascendente; los ángulos se expresan en radianes.', category: 'Trigonométrica' },
  { ...common, id: 'exponential', title: 'Exponencial decreciente', expression: 'exp(-x) - x', initial_guess: .5, description: 'Equilibrio entre una exponencial decreciente y una recta.', category: 'Exponencial' },
  { ...common, id: 'shifted-cubic', title: 'Raíz de una cúbica desplazada', expression: 'x**3 - 2*x - 5', initial_guess: 2, description: 'Aproximaciones sucesivas desde un punto cercano a la raíz.', category: 'Polinómica' },
  { ...common, id: 'logarithm', title: 'Logaritmo natural', expression: 'log(x) - 1', initial_guess: 2, description: 'La raíz es e; el punto inicial respeta el dominio x > 0.', category: 'Logarítmica' },
  { ...common, id: 'sine', title: 'Seno y una constante', expression: 'sin(x) - 0.5', initial_guess: .5, description: 'Convergencia hacia pi/6; otras raíces dependen del punto inicial.', category: 'Trigonométrica' },
  { ...common, id: 'quartic', title: 'Polinomio de cuarto grado', expression: 'x**4 - 3*x - 1', initial_guess: 1.5, description: 'Convergencia hacia una raíz positiva de una función de cuarto grado.', category: 'Polinómica' },
]
