# (c) Copyright Riverlane 2025-2026. All rights reserved.
"""2D Patch visualisation pipeline."""

from deltakit_compile.passes.common.pipeline import (
    ConfigurablePipeline,
    configurable_pass,
)
from deltakit_compile.passes.patch_lowering.rotated_surface.lower_patch_declaration import (
    LowerPatchDeclaration,
)
from deltakit_compile.passes.patch_lowering.rotated_surface.patch_to_plaquettes import (
    PatchToPlaquettes,
)
from typing_extensions import override
from xdsl.passes import ModulePass

from deltakit_visualise.passes.visualise_surface_codes import VisualiseSurfaceCodes
from deltakit_visualise.pipelines.base import VisualisationConfiguration


@configurable_pass
class PatchVisualisationPipeline(ConfigurablePipeline[VisualisationConfiguration]):
    """2D patch visualisation pipeline.

    Passes (in order):
    - VisualiseSurfaceCodes: terminal pass — generates patch/plaquette data and
      stores it on the module under SURFACE_CODES_DATA.

    Output schema: list[PatchVisualisationItem]
    """

    name = "visualise-patch-pipeline"

    verify_between_passes: bool = False

    @override
    def get_passes(self) -> tuple[ModulePass, ...]:
        return (
            LowerPatchDeclaration(),
            PatchToPlaquettes(),
            VisualiseSurfaceCodes(),
        )
