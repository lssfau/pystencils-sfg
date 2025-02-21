import pystencilssfg
from pystencilssfg.config import SfgConfig


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

            header_code = self._emitter.dumps(self._header_file)
            impl_code = (
                None
                if self._impl_file is None
                else self._emitter.dumps(self._impl_file)
            )

            mdcode = ":::::{tab-set}\n"

            mdcode += "::::{tab-item} Generated Header (.hpp)\n"
            mdcode += ":::{code-block} C++\n\n"
            mdcode += header_code
            mdcode += "\n:::\n::::\n"

            if impl_code:
                mdcode += "::::{tab-item} Generated Implementation (.cpp)\n"
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
