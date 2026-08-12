# This file contains information which is proprietary to Riverlane Ltd
# ("Riverlane") and is Riverlane Confidential Information.
# (c) Copyright Riverlane 2025-2026. All rights reserved.
"""3D spacetime visualisation pipeline."""

from deltakit_compile.passes.common.pipeline import (
    ConfigurablePipeline,
    configurable_pass,
)
from typing_extensions import override
from xdsl.passes import ModulePass

from deltakit_visualise.passes.assign_id import AssignId
from deltakit_visualise.passes.insert_height import InsertHeight
from deltakit_visualise.passes.visualise_spacetime import VisualiseSpacetime
from deltakit_visualise.pipelines.base import VisualisationConfiguration


@configurable_pass
class SpacetimePipeline(ConfigurablePipeline[VisualisationConfiguration]):
    """3D spacetime visualisation pipeline that represents the operations in a program.

    It takes IR at the logical assembly level and produces a list of
    ``SpaceTimeVisualisationItem`` objects.

    Passes (in order):
    - AssignId: shared infrastructure — assigns unique IDs to operations.
    - InsertHeight: assigns temporal ordering (z-axis) to each operation.
    - VisualiseSpacetime: terminal pass — generates SurfaceData / SidesData and
      stores it on the module under VISUALISE_SPACETIME_DATA.

    Output schema: list[SpaceTimeVisualisationItem] (SurfaceData | SidesData)
    """

    name = "visualise-spacetime-pipeline"

    verify_between_passes: bool = False

    @override
    def get_passes(self) -> tuple[ModulePass, ...]:
        return (AssignId(), InsertHeight(), VisualiseSpacetime())
