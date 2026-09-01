# (c) Copyright Riverlane 2025-2026. All rights reserved.
"""Visualisation interface for Logical-Assembly programs."""

import asyncio
import threading
from pathlib import Path
from threading import Thread

import uvicorn
from deltakit_compile.dialects.logical_assembly import LogicalAsm
from deltakit_compile.dialects.plaquette import Plaquette
from deltakit_compile.dialects.qcore import QCore
from deltakit_compile.dialects.qstruct import QStruct
from deltakit_compile.frontend.logasm import LogAsmBuilder, LogAsmProgram
from deltakit_compile.passes.common.pipeline import ConfigurablePipeline
from typing_extensions import Self
from uvicorn import Server
from xdsl.context import Context
from xdsl.dialects.arith import Arith
from xdsl.dialects.builtin import Builtin, ModuleOp
from xdsl.parser import Parser

from deltakit_visualise.api.server import create_app
from deltakit_visualise.constants import RENDER_VISUALISE_COMMAND
from deltakit_visualise.pipelines.base import VisualisationConfiguration
from deltakit_visualise.pipelines.spacetime import SpacetimePipeline
from deltakit_visualise.pipelines.surfacecodes import PatchVisualisationPipeline
from deltakit_visualise.visualiser import get_visualisation_data, show


class LogicalAssemblyVisualiser:
    """Visualisation interface for a single Logical-Assembly program / IR.

    Construct it with a program — a ``LogAsmBuilder`` (a Logical-Assembly-API
    program straight from the builder, still containing ``log_asm_api`` ops), a
    ``LogAsmProgram`` (a built program, e.g. the result of ``build_program``), or
    a ``ModuleOp`` already restricted to the ``log_asm``/``qstruct``/``arith``/
    ``builtin`` dialects ``make_context`` loads — or use one of the
    ``from_log_asm_*`` constructors. Each ``visualise_*`` method runs a
    dedicated pipeline over the program and opens the result in the browser.

    High-level use — visualise straight from a file or IR::

        >>> LogicalAssemblyVisualiser.from_log_asm_file("circuit.mlir").visualise_space_time()

    Lower-level use — drive the passes yourself (e.g. to interleave your own),
    then extract the data and render it::

        >>> ctx = LogicalAssemblyVisualiser.make_context()
        >>> SpacetimePipeline().apply(ctx, module_op)
        >>> data = get_visualisation_data(module_op)
        >>> show(data)
    """

    def __init__(
        self,
        program: LogAsmBuilder | LogAsmProgram | ModuleOp,
        *,
        verify_between_passes: bool = False,
    ) -> None:
        self.module = self._to_module(program)
        self.verify_between_passes = verify_between_passes
        self._server: Server | None = None
        self._thread: Thread | None = None
        """Whether to verify the IR between each pair of passes (testing aid)."""

    @classmethod
    def from_log_asm_file(cls, file_path: str, *, verify_between_passes: bool = False) -> Self:
        """Build a visualiser from a Logical-Assembly ``.mlir`` file."""
        return cls(
            cls.parse_mlir_file(file_path),
            verify_between_passes=verify_between_passes,
        )

    @classmethod
    def from_log_asm_ir(
        cls,
        module: LogAsmProgram | ModuleOp,
        *,
        verify_between_passes: bool = False,
    ) -> Self:
        """Build a visualiser from a built ``LogAsmProgram`` or a parsed ``ModuleOp``."""
        return cls(module, verify_between_passes=verify_between_passes)

    def visualise_space_time(self, static: bool = True) -> Path:
        """Render the 3D spacetime view in the browser.

        Args:
            static: If True (default), open the generated HTML in the system
                browser without starting an HTTP server (non-blocking). If
                False, start a blocking HTTP server on port 8899.

        Returns:
            The path to the generated ``index.html`` that is opened.
        """
        return self._visualise(
            SpacetimePipeline(verify_between_passes=self.verify_between_passes),
            static=static,
        )

    def visualise_logical_patch(self) -> Path:
        """Render the 2D logical patch (surface code) view in the browser.

        Returns the path to the generated ``index.html`` that is opened.
        """
        return self._visualise(
            PatchVisualisationPipeline(verify_between_passes=self.verify_between_passes)
        )

    def _visualise(
        self,
        pipeline: ConfigurablePipeline[VisualisationConfiguration],
        static: bool = True,
    ) -> Path:
        """Run ``pipeline`` over the bound program and open the result."""
        ctx = self.make_context()
        pipeline.apply(ctx, self.module)
        self.module.verify()
        return show(get_visualisation_data(self.module), static=static)

    @staticmethod
    def _to_module(program: LogAsmBuilder | LogAsmProgram | ModuleOp) -> ModuleOp:
        """Normalise the input to a ``ModuleOp``, building a builder if needed.

        A ``LogAsmProgram`` wraps its IR under ``.module``; a ``LogAsmBuilder`` is
        first built into a program. A ``ModuleOp`` is returned as-is.
        """
        if isinstance(program, LogAsmBuilder):
            program = program.build_program()
        if isinstance(program, LogAsmProgram):
            return program.module
        return program

    @classmethod
    def parse_mlir_file(cls, file_path: str) -> ModuleOp:
        """Parse a Logical-Assembly ``.mlir`` file and return its ``ModuleOp``."""
        try:
            with Path(file_path).open("r", encoding="utf-8") as f:
                mlir_content = f.read()
            parser = Parser(cls.make_context(), mlir_content)
            return parser.parse_module()
        except Exception as e:
            error_msg = f"Error parsing MLIR file: {e}"
            raise RuntimeError(error_msg) from e

    @staticmethod
    def make_context() -> Context:
        """Build a Context with every dialect the visualisation pipelines parse."""
        context = Context()
        context.load_dialect(Builtin)
        context.load_dialect(LogicalAsm)
        context.load_dialect(Arith)
        context.load_dialect(QStruct)
        context.load_dialect(QCore)
        context.load_dialect(Plaquette)
        return context

    def visualise(self) -> None:
        """Visualise the program in the browser.

        This is a convenience method that runs the spacetime visualisation
        pipeline and opens the result in the browser.
        """
        ctx = self.make_context()

        module_copy_for_spacetime = self.module.clone()
        SpacetimePipeline(verify_between_passes=self.verify_between_passes).apply(
            ctx, module_copy_for_spacetime
        )
        module_copy_for_spacetime.verify()

        space_time_data = get_visualisation_data(module_copy_for_spacetime)

        module_copy_for_logical_patches = self.module.clone()
        PatchVisualisationPipeline(verify_between_passes=self.verify_between_passes).apply(
            ctx, module_copy_for_logical_patches
        )
        module_copy_for_logical_patches.verify()

        logical_patches_data = get_visualisation_data(module_copy_for_logical_patches)

        app = create_app(
            space_time_data,
            logical_patches_data,
            render_command=RENDER_VISUALISE_COMMAND,
        )

        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=8000,
            log_level="info",
        )

        self._server = uvicorn.Server(config)

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            self._server.run()
        else:
            self._thread = threading.Thread(
                target=self._server.run,
                daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        """Stop the visualisation server."""
        if self._server is not None:
            self._server.should_exit = True

        if self._thread is not None:
            self._thread.join(timeout=5)
