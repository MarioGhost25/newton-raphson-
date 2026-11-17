import numpy as np
import pytest
from app.core.expression_parser import parse_expression
from app.core.newton_raphson import solve
from app.core.models import Iteration
from app.core.plot_data import initial_interval, sample_curve, tangent_points, vertical_interval


def test_tangent_passes_through_stored_point_and_intercept():
    step = solve("x**2 - 2", 1.5).iterations[0]
    x, y = tangent_points(step, (0, 2))
    assert y[np.where(x == step.x)[0][0]] == step.fx
    assert y[np.where(x == step.next_x)[0][0]] == pytest.approx(0, abs=1e-14)
    assert np.diff(y) / np.diff(x) == pytest.approx(np.full(len(x) - 1, step.derivative))


@pytest.mark.parametrize("derivative", [0, float("nan"), float("inf")])
def test_invalid_tangent_is_absent(derivative):
    step = Iteration(1, 0, 1, derivative, 1, 1, 1)
    x, y = tangent_points(step, (-1, 2))
    assert x.size == y.size == 0


@pytest.mark.parametrize("expression, pole", [("1/x", 0), ("1/(x-0.12345)**2", .12345), ("tan(x)", np.pi / 2)])
def test_poles_do_not_connect_adjacent_branches(expression, pole):
    curve = sample_curve(parse_expression(expression).expression, (pole - .8, pole + .7), 100)
    crossing = np.where((curve.x[:-1] < pole) & (curve.x[1:] > pole))[0][0]
    assert np.isnan(curve.y[crossing:crossing + 2]).all()
    assert np.isfinite(curve.y).any()
    assert curve.notice


@pytest.mark.parametrize("expression", ["log(x)", "sqrt(x)"])
def test_domain_gaps(expression):
    curve = sample_curve(parse_expression(expression).expression, (-2, 2))
    assert np.isnan(curve.y[curve.x < 0]).all()
    assert np.isfinite(curve.y[curve.x > 0]).all()


@pytest.mark.parametrize("expression, limits", [("exp(x)", (900, 1100)), ("1/0", (-1, 1))])
def test_all_non_finite_data_has_a_visual_notice(expression, limits):
    curve = sample_curve(parse_expression(expression).expression, limits)
    assert not np.isfinite(curve.y).any()
    assert curve.notice


@pytest.mark.parametrize("expression", ["2", "x**2-2", "sin(x)", "cos(x)", "exp(x)", "abs(x)"])
def test_regular_functions_have_finite_samples(expression):
    curve = sample_curve(parse_expression(expression).expression, (.2, 1.2))
    assert np.isfinite(curve.y).all()


def test_view_includes_trajectory_and_zero_without_fixed_interval():
    result = solve("x**2-10000", 150)
    limits = initial_interval(150, result)
    assert limits[0] < result.root < 150 < limits[1]
    curve = sample_curve(parse_expression("x**2-10000").expression, limits)
    bottom, top = vertical_interval(curve.y, result)
    assert bottom < 0 < top


def test_extreme_points_do_not_destroy_plot_limits():
    result = solve("x**2-2", 1e200)
    limits = initial_interval(1e200, result)
    assert np.isfinite(limits).all()
    assert max(abs(v) for v in limits) <= 1e12
