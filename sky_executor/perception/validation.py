"""Shared field rules at the report and whole-batch input boundaries."""
from math import isfinite


def is_finite_number(value) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return isfinite(value)
    except OverflowError:
        return False


def grid_cell_rejection(cell, grid_size) -> str | None:
    if not isinstance(cell, tuple) or len(cell) != 2 or any(type(value) is not int for value in cell):
        return "grid_cell must be a pair of integers"
    width, height = grid_size
    if not (0 <= cell[0] < width and 0 <= cell[1] < height):
        return f"grid_cell {cell} is outside {width}x{height}"
    return None


def confidence_rejection(confidence) -> str | None:
    if confidence is not None and (not is_finite_number(confidence) or not 0 <= confidence <= 1):
        return "confidence must be a finite number in [0, 1]"
    return None
