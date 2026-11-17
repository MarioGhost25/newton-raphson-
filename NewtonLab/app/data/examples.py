from dataclasses import dataclass


@dataclass(frozen=True)
class Example:
    title: str
    function: str
    x0: float
    description: str
    tolerance: float = 1e-8
    max_iterations: int = 100


EXAMPLES = (
    Example("Raíz cuadrada de dos", "x**2 - 2", 1.5, "Convergencia hacia la raíz positiva de un polinomio cuadrático."),
    Example("Polinomio cúbico", "x**3 - x - 2", 1.5, "Construcción geométrica de las tangentes en una función cúbica."),
    Example("Intersección con el coseno", "cos(x) - x", 1., "Una ecuación trascendente; los ángulos se expresan en radianes."),
    Example("Exponencial decreciente", "exp(-x) - x", .5, "Equilibrio entre una exponencial decreciente y una recta."),
    Example("Raíz de una cúbica desplazada", "x**3 - 2*x - 5", 2., "Aproximaciones sucesivas desde un punto cercano a la raíz."),
    Example("Logaritmo natural", "log(x) - 1", 2., "La raíz es e; el punto inicial respeta el dominio x > 0."),
    Example("Seno y una constante", "sin(x) - 0.5", .5, "Convergencia hacia pi/6; otras raíces dependen del punto inicial."),
    Example("Polinomio de cuarto grado", "x**4 - 3*x - 1", 1.5, "Convergencia hacia una raíz positiva de una función de cuarto grado."),
)
