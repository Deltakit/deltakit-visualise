# This file contains information which is proprietary to Riverlane Ltd
# ("Riverlane") and is Riverlane Confidential Information.
# (c) Copyright Riverlane 2025-2026. All rights reserved.
"""Visualise single logical patches as a demo."""

from deltakit_compile.frontend.logasm import LogAsmBuilder, RotatedPlanarPatch

from deltakit_visualise.logical_assembly_api_visualiser import LogicalAssemblyVisualiser

P_0_DISTANCE = 12

builder = LogAsmBuilder()

p0 = builder.declare_patch(RotatedPlanarPatch(P_0_DISTANCE, P_0_DISTANCE, location=(0, 0)))

p0.prepare("Z")

p0.measure_stabilisers(4)
p0.measure_stabilisers(4)


program = builder.build_program()

visualiser = LogicalAssemblyVisualiser(builder)
visualiser.visualise()
