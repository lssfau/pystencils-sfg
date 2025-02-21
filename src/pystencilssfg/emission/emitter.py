from __future__ import annotations

from pathlib import Path

from ..config import CodeStyle, ClangFormatOptions
from ..ir import SfgSourceFile

from .file_printer import SfgFilePrinter
from .clang_format import invoke_clang_format


class SfgCodeEmitter:
    def __init__(
        self,
        output_directory: Path,
        code_style: CodeStyle = CodeStyle(),
        clang_format: ClangFormatOptions = ClangFormatOptions(),
    ):
        self._output_dir = output_directory
        self._code_style = code_style
        self._clang_format_opts = clang_format
        self._printer = SfgFilePrinter(code_style)

    def dumps(self, file: SfgSourceFile) -> str:
        code = self._printer(file)

        if self._code_style.get_option("includes_sorting_key") is not None:
            sort_includes = "Never"
        else:
            sort_includes = None

        code = invoke_clang_format(
            code, self._clang_format_opts, sort_includes=sort_includes
        )

        return code

    def emit(self, file: SfgSourceFile):
        code = self.dumps(file)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        fpath = self._output_dir / file.name
        fpath.write_text(code)
