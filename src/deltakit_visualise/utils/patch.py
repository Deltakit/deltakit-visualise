# This file contains information which is proprietary to Riverlane Ltd
# ("Riverlane") and is Riverlane Confidential Information.
# (c) Copyright Riverlane 2025-2026. All rights reserved.
"""Utility function to visualise a single logical patch from a LogAsmBuilder."""

from pathlib import Path

from deltakit_compile.frontend.logasm import LogAsmBuilder, RotatedPlanarPatch

from deltakit_visualise.logical_assembly_api_visualiser import LogAsmAPIVisualiser


def visualise_logical_patch(
    builder: LogAsmBuilder, patch: RotatedPlanarPatch, round_no: int = 1
) -> Path:
    """Visualise a logical patch.

    Args:
        builder: The logical assembly builder.
        patch: The logical patch to visualise.
        round_no: Optional round number to visualise. Defaults to 1. If provided,
            only operations for that specified round are included.

    Returns:
        A Path to the generated visualisation.
    """
    api_visualiser = LogAsmAPIVisualiser(builder)
    return api_visualiser.visualise_logical_patch(patch, round_no)
