# This file contains information which is proprietary to Riverlane Ltd
# ("Riverlane") and is Riverlane Confidential Information.
# (c) Copyright Riverlane 2025-2026. All rights reserved.
"""Shared configuration for deltakit-visualise pipelines.

A visualisation pipeline is a ``ConfigurablePipeline`` whose ``get_passes`` runs
an ordered sequence of sub-passes to enrich the IR and produce visualisation
data. See :class:`~deltakit_visualise.pipelines.spacetime.SpacetimePipeline` for a
concrete example.
"""

from deltakit_compile.passes.common.pipeline import Configuration


class VisualisationConfiguration(Configuration, frozen=True):
    """Shared configuration for visualisation pipelines."""

    # TODO: Add configurable options for visualisation pipelines.
    # Stuff like ColourScheme, Default Height, etc. could be added here in the future.
