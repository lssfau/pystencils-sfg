import subprocess
import shutil

from ..config import ClangFormatOptions
from ..exceptions import SfgException


def invoke_clang_format(
    code: str, options: ClangFormatOptions, sort_includes: str | None = None
) -> str:
    """Call the `clang-format` command-line tool to format the given code string
    according to the given style arguments.

    Args:
        code: Code string to format
        options: Options controlling the clang-format invocation
        sort_includes: Option to be passed on to clang-format's ``--sort-includes`` argument

    Returns:
        The formatted code, if `clang-format` was run sucessfully.
        Otherwise, the original unformatted code, unless `codestyle.force_clang_format`
            was set to true. In the latter case, an exception is thrown.

    Forced Formatting:
        If `codestyle.force_clang_format` was set to true but the formatter could not
        be executed (binary not found, or error during exection), the function will
        throw an exception.
    """
    if options.get_option("skip"):
        return code

    binary = options.get_option("binary")
    force = options.get_option("force")
    style = options.get_option("code_style")
    args = [binary, f"--style={style}"]

    if sort_includes is not None:
        args += ["--sort-includes", sort_includes]

    if not shutil.which(binary):
        if force:
            raise SfgException(
                "`force_clang_format` was set to true in code style, "
                "but clang-format binary could not be found."
            )
        else:
            return code

    result = subprocess.run(args, input=code, capture_output=True, text=True)

    if result.returncode != 0:
        if force:
            raise SfgException(f"Call to clang-format failed: \n{result.stderr}")
        else:
            return code

    return result.stdout
