import subprocess
import shutil

from ..configuration import SfgCodeStyle
from ..exceptions import SfgException


def invoke_clang_format(code: str, codestyle: SfgCodeStyle) -> str:
    """Call the `clang-format` command-line tool to format the given code string
    according to the given style arguments.

    Args:
        code: Code string to format
        codestyle: [SfgCodeStyle][pystencilssfg.configuration.SfgCodeStyle] object
            defining the `clang-format` binary and the desired code style.

    Returns:
        The formatted code, if `clang-format` was run sucessfully.
        Otherwise, the original unformatted code, unless `codestyle.force_clang_format`
            was set to true. In the latter case, an exception is thrown.

    Forced Formatting:
        If `codestyle.force_clang_format` was set to true but the formatter could not
        be executed (binary not found, or error during exection), the function will
        throw an exception.
    """
    if codestyle.skip_clang_format:
        return code

    args = [codestyle.clang_format_binary, f"--style={codestyle.code_style}"]

    if not shutil.which(codestyle.clang_format_binary):
        if codestyle.force_clang_format:
            raise SfgException(
                "`force_clang_format` was set to true in code style, "
                "but clang-format binary could not be found."
            )
        else:
            return code

    result = subprocess.run(args, input=code, capture_output=True, text=True)

    if result.returncode != 0:
        if codestyle.force_clang_format:
            raise SfgException(f"Call to clang-format failed: \n{result.stderr}")
        else:
            return code

    return result.stdout
