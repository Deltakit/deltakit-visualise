# (c) Copyright Riverlane 2020-2026.
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest
from deltakit_compile.dialects.logical_assembly import (
    MeasStabOp,
    MeasureOp,
    MultiPauliMeasOp,
    PatchDeclarationOp,
    PrepareOp,
    RotatedPlanarPatchType,
)
from deltakit_compile.dialects.qcore import PauliAttr
from xdsl.dialects.builtin import ArrayAttr, IntAttr, NoneAttr
from xdsl.ir import SSAValue

from deltakit_visualise.utils import data as data_utils

# Type aliases for fixture callables
MakePatchDeclaration = Callable[..., PatchDeclarationOp]
MakePrepare = Callable[..., PrepareOp]
MakeMeasStab = Callable[..., MeasStabOp]
MakeMeasure = Callable[..., MeasureOp]
MakeMultiPauliMeas = Callable[..., MultiPauliMeasOp]
MakeBridgePatch = Callable[..., PatchDeclarationOp]
MakePreparedPatch = Callable[..., "PreparedPatch"]


@pytest.fixture(scope="session")
def random_generator():
    """Fixture that provides a random number generator for tests."""
    return np.random.default_rng()


@pytest.fixture
def mock_asset_reader(monkeypatch):
    """Fixture to mock get_asset_file_content for a given assets directory."""

    def _mock(assets_dir: Path) -> None:
        def mock_get_asset_file_content(relative_path: str) -> str:
            return (assets_dir / relative_path).read_text()

        # Monkeypatch on data_utils since it imports the function directly
        monkeypatch.setattr(data_utils, "get_asset_file_content", mock_get_asset_file_content)

    return _mock


@dataclass
class PrepareHtmlDirs:
    """Common directory structure for prepare_html tests."""

    js_dir: Path
    display_dir: Path
    assets_dir: Path
    umd_js_file: Path


@pytest.fixture
def prepare_html_dirs(tmp_path, monkeypatch, mock_asset_reader):
    """Set up common directory structure, UMD JS file, and monkeypatching."""
    js_dir = tmp_path / "js"
    display_dir = tmp_path / "display"
    assets_dir = tmp_path / "assets"
    js_dir.mkdir()
    display_dir.mkdir()
    assets_dir.mkdir()

    umd_js_path = "dist/deltakit-visualise.umd.js"
    umd_js_file = js_dir / umd_js_path
    umd_js_file.parent.mkdir(parents=True, exist_ok=True)
    umd_js_file.write_text("// mock js file")

    mock_asset_reader(assets_dir)
    monkeypatch.setattr(data_utils, "JS_HOME_DIR", js_dir)
    monkeypatch.setattr(data_utils, "DISPLAY_DIR", display_dir)

    return PrepareHtmlDirs(
        js_dir=js_dir,
        display_dir=display_dir,
        assets_dir=assets_dir,
        umd_js_file=umd_js_file,
    )


def make_size(x: int, y: int) -> ArrayAttr[IntAttr]:
    """Create a properly typed ArrayAttr[IntAttr] for patch size."""
    return ArrayAttr([IntAttr(x), IntAttr(y)])


@dataclass
class PreparedPatch:
    """A patch with its declaration and prepare operations."""

    patch_type: RotatedPlanarPatchType
    patch_dec: PatchDeclarationOp
    prepare: PrepareOp


@pytest.fixture
def make_patch_declaration() -> Callable[..., PatchDeclarationOp]:
    """Factory fixture to create a patch declaration."""

    def _make(width: int = 3, height: int = 3) -> PatchDeclarationOp:
        patch_type = RotatedPlanarPatchType(make_size(width, height), NoneAttr())
        return PatchDeclarationOp(patch_type)

    return _make


@pytest.fixture
def make_prepare() -> Callable[..., PrepareOp]:
    """Factory fixture to create a prepare operation."""

    def _make(
        patch: SSAValue,
        basis: PauliAttr | None = None,
    ) -> PrepareOp:
        if basis is None:
            basis = PauliAttr.Z()
        return PrepareOp(patch, basis)

    return _make


@pytest.fixture
def make_meas_stab() -> Callable[..., MeasStabOp]:
    """Factory fixture to create a meas_stab operation."""

    def _make(patch: SSAValue, rounds: int) -> MeasStabOp:
        return MeasStabOp(patch, rounds)

    return _make


@pytest.fixture
def make_measure() -> Callable[..., MeasureOp]:
    """Factory fixture to create a measure operation."""

    def _make(
        patch: SSAValue,
        basis: PauliAttr | None = None,
    ) -> MeasureOp:
        if basis is None:
            basis = PauliAttr.Z()
        return MeasureOp(patch, basis)

    return _make


@pytest.fixture
def make_multi_pauli_meas() -> Callable[..., MultiPauliMeasOp]:
    """Factory fixture to create a multi-Pauli measurement operation."""

    def _make(
        logical_patches: list[SSAValue],
        bridge_patches: list[SSAValue],
        rounds: int,
        basis: list[PauliAttr] | None = None,
    ) -> MultiPauliMeasOp:
        if basis is None:
            basis = [PauliAttr.Z()] * len(logical_patches)
        return MultiPauliMeasOp(
            rounds=rounds,
            basis=basis,
            logical_patches=logical_patches,
            bridge_patches=bridge_patches,
        )

    return _make


@pytest.fixture
def make_prepared_patch() -> Callable[..., PreparedPatch]:
    """Factory fixture to create a prepared patch with given dimensions."""

    def _make(width: int = 3, height: int = 3) -> PreparedPatch:
        patch_type = RotatedPlanarPatchType(make_size(width, height), NoneAttr())
        patch_dec = PatchDeclarationOp(patch_type)
        prepare = PrepareOp(patch_dec.res, PauliAttr.Z())
        return PreparedPatch(patch_type, patch_dec, prepare)

    return _make


@pytest.fixture
def make_bridge_patch() -> Callable[[int, int], PatchDeclarationOp]:
    """Factory fixture to create a bridge patch declaration."""

    def _make(width: int = 3, height: int = 1) -> PatchDeclarationOp:
        bridge_type = RotatedPlanarPatchType(make_size(width, height), NoneAttr())
        return PatchDeclarationOp(bridge_type)

    return _make
