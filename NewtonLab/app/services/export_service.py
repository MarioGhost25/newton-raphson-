"""Exportaciones independientes de Qt y de la figura visible."""
import csv
from datetime import datetime
from io import BytesIO, StringIO
from pathlib import Path
import os
import tempfile
from xml.sax.saxutils import escape
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, LongTable, TableStyle, PageBreak
from reportlab.platypus.doctemplate import LayoutError
from app.core.expression_parser import parse_expression
from app.core.plot_data import initial_interval, sample_curve, vertical_interval, tangent_points, VISUAL_LIMIT
from .history_service import Calculation

CSV_HEADERS = ("Iteración", "x_n", "f(x_n)", "f'(x_n)", "x_n+1", "Error absoluto")


class ExportError(Exception):
    pass


def _atomic_write(path: Path, content: bytes) -> None:
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".newtonlab-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def export_csv(calculation: Calculation, path: Path) -> None:
    if not calculation.result.iterations:
        raise ExportError("No hay iteraciones para exportar; no se generó un CSV vacío.")
    try:
        stream = StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(CSV_HEADERS)
        for step in calculation.result.iterations:
            writer.writerow((step.index, step.x, step.fx, step.derivative, step.next_x, step.absolute_error))
        _atomic_write(Path(path), stream.getvalue().encode("utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise ExportError(f"No se pudo escribir el CSV: {exc}") from exc


def _graph(calculation: Calculation, selected_index: int, palette: dict[str, str]) -> tuple[BytesIO, str]:
    parsed = parse_expression(calculation.function)
    result = calculation.result
    limits = initial_interval(calculation.x0, result)
    data = sample_curve(parsed.expression, limits)
    figure = Figure(figsize=(7, 3.2), facecolor="white")
    FigureCanvasAgg(figure)
    try:
        axes = figure.add_subplot(111)
        figure.subplots_adjust(left=.11, right=.97, bottom=.17, top=.94)
        axes.plot(data.x, data.y, color=palette["function"], linewidth=1.5, label="f(x)")
        axes.axhline(0, color="0.4", linewidth=.6)
        axes.axvline(0, color="0.6", linewidth=.6)
        points = [s.x for s in result.iterations] + [s.next_x for s in result.iterations]
        points = [v for v in points if np.isfinite(v) and abs(v) <= VISUAL_LIMIT]
        axes.plot(points, np.zeros(len(points)), "o", color=palette["iteration"], markersize=3, label="Iteraciones")
        if result.iterations:
            index = max(0, min(selected_index, len(result.iterations) - 1))
            step = result.iterations[index]
            x, y = tangent_points(step, limits)
            axes.plot(x, y, color=palette["tangent"], label=f"Tangente n={step.index}", linewidth=1)
            if max(abs(step.x), abs(step.fx), abs(step.next_x)) <= VISUAL_LIMIT:
                axes.plot([step.x], [step.fx], "o", color=palette["iteration"], markersize=5)
                axes.plot([step.next_x], [0], "o", color=palette["reference"], markersize=4)
        if result.converged and abs(result.root) <= VISUAL_LIMIT:
            axes.plot([result.root], [0], "o", color=palette["root"], label="Raíz", markersize=6)
        axes.set_xlim(limits)
        axes.set_ylim(vertical_interval(data.y, result))
        axes.set_xlabel("x", fontsize=9)
        axes.set_ylabel("f(x)", fontsize=9)
        axes.tick_params(labelsize=8)
        axes.grid(color="0.85", linewidth=.5)
        axes.legend(fontsize=8, loc="best")
        stream = BytesIO()
        figure.savefig(stream, format="png", dpi=200)
        stream.seek(0)
        notice = data.notice
        if any(abs(v) > VISUAL_LIMIT for v in [calculation.x0, result.root] + [s.fx for s in result.iterations]):
            notice += " Algunos puntos exceden el límite visual de +/-1e12."
        return stream, notice
    finally:
        figure.clear()


def export_pdf(calculation: Calculation, path: Path, palette: dict[str, str], selected_index: int = 0) -> None:
    try:
        result = calculation.result
        styles = getSampleStyleSheet()
        body = ParagraphStyle("Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=9, leading=13, spaceAfter=5)
        heading = ParagraphStyle("Section", parent=styles["Heading2"], fontSize=12, spaceBefore=8, spaceAfter=7)
        cell = ParagraphStyle("Cell", parent=body, fontSize=7, leading=9, alignment=2, spaceAfter=0)
        def p(text: str, style=body):
            return Paragraph(escape(text), style)
        def number(value: float | None) -> str:
            return "No disponible" if value is None else f"{value:.12g}"
        generated = datetime.now().astimezone().strftime("%d/%m/%Y %H:%M:%S %z")
        content = [p("NewtonLab", styles["Title"]), p("Método de Newton-Raphson", styles["Heading2"]),
                   p(f"Generado: {generated}"), p("Datos de entrada", heading),
                   p(f"f(x) = {calculation.function}"), p(f"f'(x) = {calculation.derivative}"),
                   p(f"x inicial: {number(calculation.x0)}    |    Tolerancia: {number(calculation.tolerance)}    |    Máximo: {calculation.max_iterations}"),
                   p("Resultado", heading), p(f"Estado: {result.status.value}"),
                   p(f"Raíz aproximada: {number(result.root)}" if result.converged else "No se obtuvo una raíz con convergencia confirmada."),
                   p(f"Última aproximación: {number(result.root)}" if not result.converged else result.message)]
        if not result.converged:
            content.append(p(result.message))
        content.extend([p(f"Residuo absoluto: {number(result.residual)}    |    Error final: {number(result.iterations[-1].absolute_error if result.iterations else None)}"),
                        p(f"Iteraciones completadas: {len(result.iterations)}"), p("Visualización", heading)])
        graph, notice = _graph(calculation, selected_index, palette)
        content.append(Image(graph, width=499, height=228))
        content.append(p("Vista automática del recorrido; la vista de la aplicación no se modifica."))
        if notice:
            content.append(p(notice))
        content.extend([PageBreak(), p("Procedimiento e iteraciones", heading),
                        p("x_(n+1) = x_n - f(x_n) / f'(x_n)"),
                        p("Criterio: error absoluto y residuo <= tolerancia. Valores mostrados con hasta 12 cifras significativas.")])
        if result.iterations:
            rows = [[p(header, cell) for header in CSV_HEADERS]]
            rows.extend([[p(str(step.index), cell)] + [p(number(v), cell) for v in
                         (step.x, step.fx, step.derivative, step.next_x, step.absolute_error)] for step in result.iterations])
            table = LongTable(rows, colWidths=[49, 90, 90, 90, 90, 90], repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCDDE0")),
                                       ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F3F3")]),
                                       ("LINEBELOW", (0, 0), (-1, 0), .5, colors.grey),
                                       ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                       ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
            content.append(table)
        else:
            content.append(p("No se completaron iteraciones. " + result.message))
        output = BytesIO()
        document = SimpleDocTemplate(output, pagesize=A4, leftMargin=48, rightMargin=48,
                                     topMargin=42, bottomMargin=42, title="NewtonLab - Reporte de cálculo", author="NewtonLab")
        def footer(canvas, doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.grey)
            canvas.drawString(48, 24, "NewtonLab | Método de Newton-Raphson")
            canvas.drawRightString(A4[0] - 48, 24, f"Página {doc.page}")
            canvas.restoreState()
        document.build(content, onFirstPage=footer, onLaterPages=footer)
        _atomic_write(Path(path), output.getvalue())
    except (OSError, ValueError, RuntimeError, LayoutError) as exc:
        raise ExportError(f"No se pudo generar el PDF: {exc}") from exc
