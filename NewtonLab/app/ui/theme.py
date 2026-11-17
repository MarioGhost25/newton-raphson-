"""Única fuente de colores de interfaz y representación matemática."""
COLORS = {
    "background": "#090A0C",
    "panel": "#141518",
    "control": "#222428",
    "border": "#303238",
    "text": "#EEEEF0",
    "secondary": "#9699A1",
    "grid": "#272930",
    "primary": "#DCDDE0",
    "function": "#74A9FF",
    "tangent": "#EEA66D",
    "iteration": "#B19AF7",
    "reference": "#E78DA6",
    "root": "#8FC5A6",
}


def stylesheet() -> str:
    from pathlib import Path
    template = Path(__file__).with_name("styles.qss").read_text(encoding="utf-8")
    for name, color in COLORS.items():
        template = template.replace("@" + name + "@", color)
    return template
