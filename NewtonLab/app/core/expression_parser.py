"""Gramática AST cerrada: nunca se ejecuta el texto introducido."""
import ast
import re
from dataclasses import dataclass
import sympy as sp

X = sp.Symbol("x", real=True)
FUNCTIONS = {name: getattr(sp, name) for name in
             ("sin", "cos", "tan", "asin", "acos", "atan", "sinh", "cosh", "tanh", "exp", "log", "sqrt")}
FUNCTIONS["abs"] = sp.Abs
CONSTANTS = {"x": X, "pi": sp.pi, "e": sp.E, "E": sp.E}


class ExpressionError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedExpression:
    expression: sp.Expr
    derivative: sp.Expr


def normalize_expression(source: str) -> str:
    """Normaliza notación matemática; el AST cerrado sigue siendo la autoridad."""
    if not isinstance(source, str) or not source.strip() or len(source) > 512:
        raise ExpressionError("Introducí una función de hasta 512 caracteres.")
    source = re.sub(r"[⁰¹²³⁴⁵⁶⁷⁸⁹]+", lambda m: "**" + m[0].translate(
        str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")), source).replace("^", "**").replace("−", "-")
    tokens = []
    position = 0
    pattern = re.compile(r"\s+|(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?|[A-Za-z_][A-Za-z_0-9]*|\*\*|[+*/()-]")
    for match in pattern.finditer(source):
        if match.start() != position:
            raise ExpressionError("Símbolo no permitido en la función.")
        position = match.end()
        token = match[0]
        if token.isspace():
            continue
        if token[0].isalpha() or token[0] == "_":
            if token not in CONSTANTS and token not in FUNCTIONS:
                raise ExpressionError("Nombre no permitido en la función.")
        if token == "x" and tokens and re.fullmatch(r"(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", tokens[-1]):
            tokens.append("*")
        tokens.append(token)
    if position != len(source):
        raise ExpressionError("Símbolo no permitido en la función.")
    return " ".join(tokens)


def parse_expression(source: str) -> ParsedExpression:
    if not isinstance(source, str) or not source.strip():
        raise ExpressionError("Introducí una función de x.")
    if len(source) > 512:
        raise ExpressionError("La función admite hasta 512 caracteres.")
    try:
        tree = ast.parse(normalize_expression(source), mode="eval")
    except (SyntaxError, ValueError, RecursionError) as exc:
        raise ExpressionError("Expresión inválida. Usá * para multiplicar y ** para potencias.") from exc
    if sum(1 for _ in ast.walk(tree)) > 128:
        raise ExpressionError("La expresión es demasiado compleja.")

    def convert(node: ast.AST, depth: int = 0) -> sp.Expr:
        if depth > 20:
            raise ExpressionError("La expresión tiene demasiados niveles.")
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            if abs(node.value) > 1e100:
                raise ExpressionError("Constante fuera del rango permitido.")
            return sp.sympify(node.value)
        if isinstance(node, ast.Name) and node.id in CONSTANTS:
            return CONSTANTS[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = convert(node.operand, depth + 1)
            if isinstance(node.op, ast.UAdd):
                return value
            return -value if value.is_Number else sp.Mul(-1, value, evaluate=False)
        if isinstance(node, ast.BinOp):
            left, right = convert(node.left, depth + 1), convert(node.right, depth + 1)
            if isinstance(node.op, ast.Add):
                return sp.Add(left, right, evaluate=False)
            if isinstance(node.op, ast.Sub):
                negative = -right if right.is_Number else sp.Mul(-1, right, evaluate=False)
                return sp.Add(left, negative, evaluate=False)
            if isinstance(node.op, ast.Mult):
                return sp.Mul(left, right, evaluate=False)
            if isinstance(node.op, ast.Div):
                return sp.Mul(left, sp.Pow(right, -1, evaluate=False), evaluate=False)
            if isinstance(node.op, ast.Pow):
                # Exponentes numéricos simples evitan torres de potencias costosas.
                if not right.is_Symbol and not right.is_Number:
                    raise ExpressionError("Usá un exponente numérico simple o x; para otros casos, exp().")
                if right.is_Number and abs(right) > 100:
                    raise ExpressionError("El exponente numérico debe estar entre -100 y 100.")
                return sp.Pow(left, right, evaluate=False)
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in FUNCTIONS and len(node.args) == 1 and not node.keywords):
            return FUNCTIONS[node.func.id](convert(node.args[0], depth + 1), evaluate=False)
        raise ExpressionError("Entrada no permitida. Usá x, números, +, -, *, /, ** y funciones admitidas.")

    try:
        expression = convert(tree.body)
        return ParsedExpression(expression, sp.diff(expression, X))
    except ExpressionError:
        raise
    except (ValueError, TypeError, OverflowError, RecursionError) as exc:
        raise ExpressionError("No se pudo interpretar o derivar la función.") from exc
