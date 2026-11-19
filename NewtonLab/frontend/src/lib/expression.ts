const functions = new Set('sin cos tan asin acos atan sinh cosh tanh exp log sqrt abs'.split(' '))
const constants = new Set(['x', 'pi', 'e', 'E'])
const number = /^(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$/

// Sólo normaliza y comprueba sintaxis. El AST del servidor valida y calcula.
export function normalizeExpression(input: string): string {
  const invalid = () => new Error('Usá x, números, operadores y funciones admitidas; revisá la sintaxis.')
  if (!input.trim() || input.length > 512) throw invalid()
  const source = input.replace(/[⁰¹²³⁴⁵⁶⁷⁸⁹]+/g, digits => '**' + [...digits].map(digit => '⁰¹²³⁴⁵⁶⁷⁸⁹'.indexOf(digit)).join(''))
    .replace(/\^/g, '**').replace(/−/g, '-')
  const pattern = /\s+|(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?|[A-Za-z_][A-Za-z_0-9]*|\*\*|[+*/()-]/gy
  const tokens: string[] = []
  let position = 0
  while (position < source.length) {
    pattern.lastIndex = position
    const match = pattern.exec(source)
    if (!match) throw invalid()
    position = pattern.lastIndex
    const token = match[0]
    if (!token.trim()) continue
    if (token === 'x' && number.test(tokens.at(-1) ?? '')) tokens.push('*')
    tokens.push(token)
  }
  let operand = true
  let depth = 0
  let needCall = false
  tokens.forEach(token => {
    if (needCall && token !== '(') throw invalid()
    if (token === '(') {
      if (!operand || ++depth > 20) throw invalid()
      needCall = false
    } else if (token === ')') {
      if (operand || --depth < 0) throw invalid()
    } else if (functions.has(token)) {
      if (!operand) throw invalid()
      needCall = true
    } else if (constants.has(token) || number.test(token)) {
      if (!operand || (number.test(token) && (!Number.isFinite(Number(token)) || Math.abs(Number(token)) > 1e100))) throw invalid()
      operand = false
    } else if (['+', '-', '*', '/', '**'].includes(token)) {
      if (operand && token !== '+' && token !== '-') throw invalid()
      operand = true
    } else throw invalid()
  })
  if (operand || depth || needCall) throw invalid()
  return tokens.join(' ')
}
