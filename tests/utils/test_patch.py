# (c) Copyright Riverlane 2020-2026.
"""Tests for utils/patch.py."""

from pathlib import Path

import pytest
from deltakit_compile.frontend.logasm import LogAsmBuilder, RotatedPlanarPatch

from deltakit_visualise.utils.patch import visualise_logical_patch


@pytest.fixture
def builder_and_patch():
    """Builder with a single prepared patch."""
    builder = LogAsmBuilder()
    p = builder.declare_patch(RotatedPlanarPatch(5, 5, location=(0, 0)))
    p.prepare("Z")
    p.measure_stabilisers(4)
    return builder, p


class TestVisualiseLogicalPatch:
    """Tests for the visualise_logical_patch utility function."""

    def test_delegates_to_api_visualiser(self, monkeypatch, builder_and_patch):
        """visualise_logical_patch calls LogAsmAPIVisualiser.visualise_logical_patch."""
        builder, p = builder_and_patch
        calls: list = []

        def fake_visualise(_self, patch_arg, round_no=None):
            calls.append((patch_arg, round_no))
            return Path("/display/index.html")

        monkeypatch.setattr(
            "deltakit_visualise.logical_assembly_api_visualiser.LogAsmAPIVisualiser"
            ".visualise_logical_patch",
            fake_visualise,
        )

        visualise_logical_patch(builder, p)

        assert len(calls) == 1
        assert calls[0] == (p, 1)

    def test_two_patches_produce_different_visualisations(self, monkeypatch, builder_and_patch):
        """Calling the utility for two different patches yields different data."""
        builder, _ = builder_and_patch
        p1 = builder.declare_patch(RotatedPlanarPatch(12, 12, location=(5, 5)))
        p1.prepare("X")
        p1.measure_stabilisers(4)

        datasets: list[dict] = []

        def fake_show(data, **_kwargs):
            datasets.append(data)
            return Path("/display/index.html")

        monkeypatch.setattr("deltakit_visualise.logical_assembly_api_visualiser.show", fake_show)

        _, p0 = builder_and_patch
        visualise_logical_patch(builder, p0)
        visualise_logical_patch(builder, p1)

        assert len(datasets) == 2
        assert str(datasets[0]) != str(datasets[1])
