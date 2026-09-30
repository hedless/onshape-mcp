"""Length unit for every length the tools accept and report.

The Onshape API works in meters. Tool arguments and tool output use the unit set in the
ONSHAPE_LENGTH_UNIT environment variable (in, mm, cm or m), inches when it is unset.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LengthUnit:
    """A length unit as the tools use it."""

    name: str  # plural, for tool descriptions and output: "inches"
    expression: str  # unit in an Onshape expression: "in"
    symbol: str  # suffix after a number in tool output: '"'
    meters: float  # length of one unit in meters


LENGTH_UNITS = {
    "in": LengthUnit("inches", "in", '"', 0.0254),
    "mm": LengthUnit("millimeters", "mm", " mm", 0.001),
    "cm": LengthUnit("centimeters", "cm", " cm", 0.01),
    "m": LengthUnit("meters", "m", " m", 1.0),
}


def length_unit() -> LengthUnit:
    """Return the unit set in ONSHAPE_LENGTH_UNIT, inches when unset.

    Raises:
        ValueError: If the variable holds an unsupported unit
    """
    key = os.getenv("ONSHAPE_LENGTH_UNIT", "in").strip().lower() or "in"
    if key not in LENGTH_UNITS:
        raise ValueError(
            f"Unsupported ONSHAPE_LENGTH_UNIT '{key}'. Use one of: {', '.join(LENGTH_UNITS)}"
        )
    return LENGTH_UNITS[key]


def to_meters(value: float) -> float:
    """Convert a length in the configured unit to meters."""
    return value * length_unit().meters


def from_meters(value: float) -> float:
    """Convert a length in meters to the configured unit."""
    return value / length_unit().meters


def length_expression(value: float) -> str:
    """Onshape expression for a length in the configured unit, e.g. '2.5 cm'."""
    return f"{value} {length_unit().expression}"


def format_length(value: float, decimals: int = 3) -> str:
    """Format a length in the configured unit for tool output, e.g. '2.500 cm'."""
    return f"{value:.{decimals}f}{length_unit().symbol}"
