# (c) Copyright Riverlane 2026-2026. All rights reserved.
"""Visualise single logical patches as a demo."""

from deltakit_compile.frontend.logasm import LogAsmBuilder, RotatedPlanarPatch

from deltakit_visualise.logical_assembly_api_visualiser import LogicalAssemblyVisualiser

builder = LogAsmBuilder()

p0 = builder.declare_patch(
    RotatedPlanarPatch(4, 4, location=(0, 0), vertical_z=True),
)
bridge = builder.declare_patch(
    RotatedPlanarPatch(4, 4, location=(0, 4), vertical_z=True),
)

p0.prepare("X")
p0.measure_stabilisers(min_rounds=4)
p0.move((0, 8), bridges=[bridge])
p0.measure_stabilisers(min_rounds=4)

program = builder.build_program()

# print(program)

visualiser = LogicalAssemblyVisualiser(builder)
visualiser.visualise_space_time()
