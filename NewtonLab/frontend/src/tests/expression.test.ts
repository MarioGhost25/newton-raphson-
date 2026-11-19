import { expect, it } from 'vitest'
import { defaults, validate } from '@/hooks/useCalculation'
import { normalizeExpression } from '@/lib/expression'

it.each([
  ['x² - 0.5', 'x ** 2 - 0.5'],
  ['x^3 - x - 2', 'x ** 3 - x - 2'],
  ['2x³ + 6x² - 8x + 2', '2 * x ** 3 + 6 * x ** 2 - 8 * x + 2'],
  ['x**2', 'x ** 2'], ['1e-3x² − .5x', '1e-3 * x ** 2 - .5 * x'],
  ['cos(x)-x', 'cos ( x ) - x'], ['x¹⁰', 'x ** 10'],
])('normaliza %s sin evaluar', (source, expected) => {
  expect(normalizeExpression(source)).toBe(expected)
  expect(validate({ ...defaults, expression: source }).errors).toEqual({})
})

it.each(['x +', 'y', '__import__("os")', 'x.__class__', 'sin(x,x)', '1e309', 'x//2', 'x%2', 'lambda x: x', '2 3', 'sin x', 'x² # comment', 'x²; print(1)', '(x', 'x)'])('rechaza %s antes de enviar', expression => {
  expect(validate({ ...defaults, expression }).errors.expression).toBeTruthy()
})
