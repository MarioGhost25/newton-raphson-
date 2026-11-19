import math
import pytest
from app.core.expression_parser import ExpressionError, parse_expression
from app.core.models import Status
from app.core.newton_raphson import solve


@pytest.mark.parametrize("function, initial, expected", [
    ("x**2 - 2", 1.5, math.sqrt(2)),
    ("x**3 - x - 2", 1.5, 1.5213797068045676),
    ("cos(x) - x", 1, 0.7390851332151607),
    ("exp(x) - 2", 1, math.log(2)),
    ("log(x) - 1", 2, math.e),
    ("x**-2 - 4", 0.4, 0.5),
])
def test_convergence(function, initial, expected):
    result = solve(function, initial)
    assert result.converged
    assert result.root == pytest.approx(expected, abs=1e-8)
    assert result.residual <= 1e-8
    assert result.iterations[-1].absolute_error <= 1e-8
    for step in result.iterations:
        assert step.next_x == pytest.approx(step.x - step.fx / step.derivative)
        assert step.absolute_error == abs(step.next_x - step.x)
    for previous, following in zip(result.iterations, result.iterations[1:]):
        assert previous.next_x == following.x


@pytest.mark.parametrize("function", ["x**2 + 1", "1e-14*x + 1"])
def test_zero_derivative(function):
    assert solve(function, 0).status is Status.ZERO_DERIVATIVE


@pytest.mark.parametrize("source", ["", "x +", "y + 1", "__import__('os')", "x.__class__",
                                   "[x for x in [1]]", "open('file')", "sin(x, x)", "True", "9**9**9", "1e309"])
def test_reject_invalid_or_unsafe_expression(source):
    with pytest.raises(ExpressionError):
        parse_expression(source)


@pytest.mark.parametrize("function, initial", [("log(x)", -1), ("sqrt(x)", -1), ("log(x)+10", 1)])
def test_domain_error(function, initial):
    assert solve(function, initial).status is Status.DOMAIN_ERROR


@pytest.mark.parametrize("function, initial", [("1/x", 0), ("exp(x)", 1000)])
def test_non_finite(function, initial):
    assert solve(function, initial).status is Status.NON_FINITE


def test_no_convergence():
    result = solve("x**3 - 2*x + 2", 0, max_iterations=8)
    assert result.status is Status.MAX_ITERATIONS
    assert len(result.iterations) == 8


def test_small_step_does_not_imply_small_residual():
    result = solve("1e20*x**2 - 2", 1e-10, tolerance=1e-8, max_iterations=1)
    assert result.iterations[0].absolute_error < 1e-8
    assert result.residual > 1e-8
    assert not result.converged


def test_exact_initial_root_with_zero_derivative():
    result = solve("x**2", 0)
    assert result.converged
    assert result.iterations == ()


@pytest.mark.parametrize("kwargs", [{"tolerance": 0}, {"tolerance": -1}, {"tolerance": math.nan},
                                    {"x0": math.inf}, {"max_iterations": 0}, {"max_iterations": 1.5},
                                    {"max_iterations": True}, {"max_iterations": 1001}])
def test_invalid_parameters(kwargs):
    with pytest.raises(ValueError):
        solve("x**2 - 2", **kwargs)


@pytest.mark.parametrize("natural, explicit", [
    ("x² - 0.5", "x**2 - 0.5"),
    ("x^3 - x - 2", "x**3 - x - 2"),
    ("2x³ + 6x² - 8x + 2", "2*x**3 + 6*x**2 - 8*x + 2"),
    ("1e-3x² − .5x", "1e-3*x**2 - .5*x"),
    ("x¹⁰", "x**10"),
])
def test_natural_notation_preserves_calculations(natural, explicit):
    assert parse_expression(natural) == parse_expression(explicit)
    actual, expected = solve(natural), solve(explicit)
    assert actual == expected
    for step in actual.iterations:
        assert step.absolute_error == abs(step.next_x - step.x)


@pytest.mark.parametrize("source", ["2x.__class__", "x²; print(1)", "x^__import__('os')", "x//2", "x%2", "lambda x: x", "2 3", "sin x", "x² # comment"])
def test_natural_notation_rejects_python(source):
    with pytest.raises(ExpressionError):
        parse_expression(source)
