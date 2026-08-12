"""CLI driver for deltakit-visualise filecheck tests.

Parses an MLIR file, runs it through the selected visualisation view, and
writes the JSON result to stdout or a file.

Usage
-----
    python visualise.py <mlir_file> [--view <view>] [-O <output_file>]

    --view   View to render. One of the keys in VIEWS (default:
             "spacetime_visualisation").
    -O       Write JSON output to this file instead of stdout.

Filecheck substitutions (defined in lit.cfg.py)
------------------------------------------------------
    %visualise        spacetime_visualisation view (default)

    %visualise_patch  patch_visualisation view
"""

import argparse
import json
import sys
from pathlib import Path

from deltakit_visualise.logical_assembly_visualiser import LogicalAssemblyVisualiser
from deltakit_visualise.pipelines.spacetime import SpacetimePipeline
from deltakit_visualise.pipelines.surfacecodes import PatchVisualisationPipeline
from deltakit_visualise.visualiser import get_visualisation_data

# The --view names this driver accepts.
_VIEWS = [
    "spacetime_visualisation",
    "patch_visualisation",
]


def visualise() -> None:
    """Run the selected visualisation view and emit JSON output."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mlir_file", type=Path, help="Path to the MLIR file to visualise")
    parser.add_argument(
        "--view",
        default="spacetime_visualisation",
        choices=_VIEWS,
        help="Visualisation view to render (default: spacetime_visualisation)",
    )
    parser.add_argument("-O", "--output", type=Path, help="Write JSON output to this file")
    args = parser.parse_args()

    ctx = LogicalAssemblyVisualiser.make_context()
    module_op = LogicalAssemblyVisualiser.parse_mlir_file(args.mlir_file)

    if args.view == "spacetime_visualisation":
        SpacetimePipeline().apply(ctx, module_op)
    elif args.view == "patch_visualisation":
        PatchVisualisationPipeline().apply(ctx, module_op)

    data = get_visualisation_data(module_op)
    json_result = json.dumps(data)
    if args.output:
        with Path(args.output).open("w", encoding="utf-8") as f:
            f.write(json_result)
    else:
        sys.stdout.write(json_result)


if __name__ == "__main__":
    visualise()
