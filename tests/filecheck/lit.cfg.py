"""
Test configuration for running deltakit_visualise tests with LLVM's lit framework.

Sets up test formats, source roots, suffixes, and substitutions
for deltakit_visualise filecheck tests.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any

import lit.formats

if TYPE_CHECKING:
    config: Any  # Provided by lit at runtime
    lit_config: Any

# Test root configuration
config.test_source_root = str(Path(__file__).parent)
deltakit_visualise_src = str(Path(config.test_source_root).parent.parent)
filecheck_dir = str(Path(deltakit_visualise_src) / "tests" / "filecheck")

# lit config
config.name = "deltakit-visualise"
config.suffixes = [".mlir"]
config.excludes = ["lit.cfg.py"]

config.test_format = lit.formats.ShTest(
    preamble_commands=[
        f"cd {deltakit_visualise_src}",
    ],
)

# Command substitutions
# %visualise       — spacetime_visualisation pipeline (3D view, default)
# %visualise_patch — patch visualisation pipeline (2D surface code view)
config.substitutions.extend(
    [
        ("%visualise", f"python {filecheck_dir}/visualise.py"),
        ("%filecheck", "filecheck"),
    ]
)

if "COVERAGE" in lit_config.params:
    source_path = lit_config.params["COVERAGE"]
    SOURCE_ARG = f"--source {source_path},deltakit_visualise" if source_path != "" else ""
    config.substitutions.insert(
        0,
        (
            "%visualise_patch",
            f"coverage run -p {SOURCE_ARG} {filecheck_dir}/visualise.py",
        ),
    )
    config.substitutions.insert(
        1,
        (
            "%visualise",
            f"coverage run -p {SOURCE_ARG} {filecheck_dir}/visualise.py",
        ),
    )
