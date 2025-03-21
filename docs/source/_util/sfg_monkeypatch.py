import pystencilssfg
from pystencilssfg.config import SfgConfig

from os.path import splitext


class DocsPatchedGenerator(pystencilssfg.SourceFileGenerator):
    """Mockup wrapper around SourceFileGenerator for use in documentation
    notebooks to print the generated code directly to the HTML
    instead of writing it to file."""

    scriptname: str = "demo"
    glue: bool = False
    display: bool = True

    @classmethod
    def setup(cls, scriptname: str, glue: bool = False, display: bool = True):
        cls.scriptname = scriptname
        cls.glue = glue
        cls.display = display

    def _scriptname(self) -> str:
        return f"{DocsPatchedGenerator.scriptname}.py"

    def __init__(
        self, sfg_config: SfgConfig | None = None, keep_unknown_argv: bool = False
    ):
        super().__init__(sfg_config, keep_unknown_argv=True)

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self._finish_files()
            emitter = self._get_emitter()

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
