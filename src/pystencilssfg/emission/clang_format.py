import subprocess
import shutil

from ..configuration import SfgCodeStyle
from ..exceptions import SfgException


def invoke_clang_format(code: str, codestyle: SfgCodeStyle) -> str:
    args = [codestyle.clang_format_binary, f"--style={codestyle.code_style}"]

    if not shutil.which(codestyle.clang_format_binary):
        return code

    result = subprocess.run(args, input=code, capture_output=True, text=True)

    if result.returncode != 0:
        if codestyle.force_clang_format:
            raise SfgException(f"Call to clang-format failed: \n{result.stderr}")
        else:
            return code

    return result.stdout
