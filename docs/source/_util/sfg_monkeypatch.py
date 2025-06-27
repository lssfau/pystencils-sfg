import pystencilssfg
from pystencilssfg.config import SfgConfig

from os.path import splitext
from pathlib import Path


class DocsPatchedGenerator(pystencilssfg.SourceFileGenerator):
    """Mockup wrapper around SourceFileGenerator for use in documentation
    notebooks to print the generated code directly to the HTML
    instead of writing it to file."""

    scriptname: str = "demo"
    glue: bool = False
    display: bool = True
    output_dir: str | None = None

    @classmethod
    def setup(
        cls,
        scriptname: str,
        glue: bool = False,
        display: bool = True,
        output_dir: str | None = None,
    ):
        cls.scriptname = scriptname
        cls.glue = glue
        cls.display = display
        cls.output_dir = output_dir

    def _scriptname(self) -> str:
        return f"{DocsPatchedGenerator.scriptname}.py"

    def __init__(
        self, sfg_config: SfgConfig | None = None, keep_unknown_argv: bool = False
    ):
        if DocsPatchedGenerator.output_dir:
            sfg_config = sfg_config.copy() if sfg_config is not None else SfgConfig()
            sfg_config.output_directory = DocsPatchedGenerator.output_dir
        super().__init__(sfg_config, keep_unknown_argv=True)

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self._finish_files()
            emitter = self._get_emitter()

            if DocsPatchedGenerator.output_dir:
                emitter.emit(self._header_file)
                if self._impl_file is not None:
                    emitter.emit(self._impl_file)

            header_code = emitter.dumps(self._header_file)
            header_ext = splitext(self._header_file.name)[1]

            mdcode = ":::::{tab-set}\n"

            mdcode += f"::::{{tab-item}} Generated Header ({header_ext})\n"
            mdcode += ":::{code-block} C++\n\n"
            mdcode += header_code
            mdcode += "\n:::\n::::\n"

            if self._impl_file is not None:
                impl_code = emitter.dumps(self._impl_file)
                impl_ext = splitext(self._impl_file.name)[1]

                mdcode += f"::::{{tab-item}} Generated Implementation ({impl_ext})\n"
                mdcode += ":::{code-block} C++\n\n"
                mdcode += impl_code
                mdcode += "\n:::\n::::\n"

            mdcode += ":::::"
            from IPython.display import Markdown

            mdobj = Markdown(mdcode)

            if self.glue:
                from myst_nb import glue

                glue(f"sfg_out_{self.scriptname}", mdobj, display=False)

            if self.display:
                from IPython.display import display

                display(mdobj)


pystencilssfg.SourceFileGenerator = DocsPatchedGenerator
