"""Height attribute extraction utilities."""

from xdsl.dialects.builtin import FloatAttr, IntAttr
from xdsl.ir import Operation

from deltakit_visualise.constants import END_HEIGHT_ATTR, START_HEIGHT_ATTR


def get_start_height(op: Operation) -> float:
    """Get the start_height attribute from an operation."""
    attr = op.attributes.get(START_HEIGHT_ATTR)
    if isinstance(attr, IntAttr):
        return float(attr.data)
    if isinstance(attr, FloatAttr):
        return attr.value.data
    msg = f"Operation {op.name} is missing a valid {START_HEIGHT_ATTR} attribute"
    raise ValueError(msg)


def get_end_height(op: Operation) -> float:
    """Get the end_height attribute from an operation."""
    attr = op.attributes.get(END_HEIGHT_ATTR)
    if isinstance(attr, IntAttr):
        return float(attr.data)
    if isinstance(attr, FloatAttr):
        return attr.value.data
    msg = f"Operation {op.name} is missing a valid {END_HEIGHT_ATTR} attribute"
    raise ValueError(msg)
