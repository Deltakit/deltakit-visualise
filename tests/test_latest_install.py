# (c) Copyright Riverlane 2025-2026. All rights reserved.
"""Integration test for fresh wheel installation verification.

This test verifies that the installed deltakit-visualise wheel can execute
end-to-end without errors on real filecheck MLIR test files.
"""

from pathlib import Path

import pytest
from deltakit_compile.dialects.qcore import AllocQubitOp

from deltakit_visualise.logical_assembly_visualiser import LogicalAssemblyVisualiser
from deltakit_visualise.pipelines.spacetime import SpacetimePipeline
from deltakit_visualise.pipelines.surfacecodes import PatchVisualisationPipeline
from deltakit_visualise.visualiser import get_visualisation_data

# Find all MLIR files in the filecheck directory
FILECHECK_DIR = Path(__file__).parent / "filecheck"
MLIR_FILES = sorted(FILECHECK_DIR.glob("**/*.mlir"))


@pytest.mark.parametrize(
    "mlir_file",
    MLIR_FILES,
    ids=[str(f.relative_to(FILECHECK_DIR)) for f in MLIR_FILES],
)
def test_visualise_on_all_filecheck(mlir_file):
    """Integration test: verify visualiser can process all filecheck MLIR files without error.

    This test runs on a freshly installed wheel to ensure:
    - The visualiser module can be imported
    - A pipeline can be applied and its data extracted
    - Each MLIR test file can be processed end-to-end
    """
    ctx = LogicalAssemblyVisualiser.make_context()
    module_op = LogicalAssemblyVisualiser.parse_mlir_file(str(mlir_file))

    has_alloc_qubit = any(isinstance(op, AllocQubitOp) for op in module_op.walk())
    if has_alloc_qubit:
        PatchVisualisationPipeline().apply(ctx, module_op)
    else:
        SpacetimePipeline().apply(ctx, module_op)

    data = get_visualisation_data(module_op)

    # Verify result is a valid output structure
    assert "ops" in data
    assert isinstance(data["ops"], list)
