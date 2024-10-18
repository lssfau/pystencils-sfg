import pytest

from dataclasses import dataclass

import os
from os import path
import shutil
import subprocess

THIS_DIR = path.split(__file__)[0]
SCRIPTS_DIR = path.join(THIS_DIR, "scripts")
EXPECTED_DIR = path.join(THIS_DIR, "expected")


@dataclass
class ScriptInfo:
    @staticmethod
    def make(name, *args, **kwargs):
        return pytest.param(ScriptInfo(name, *args, **kwargs), id=f"{name}.py")

    script_name: str
    """Name of the generator script, without .py-extension.

    Generator scripts must be located in the ``scripts`` folder.
    """

    expected_outputs: tuple[str, ...]
    """List of file extensions expected to be emitted by the generator script.

    Output files will all be placed in the ``out`` folder.
    """

    compilable_output: str | None = None
    """File extension of the output file that can be compiled.

    If this is set, and the expected file exists, the ``compile_cmd`` will be
    executed to check for error-free compilation of the output.
    """

    compile_cmd: str = f"g++ --std=c++17 -I {THIS_DIR}/deps/mdspan/include"
    """Command to be invoked to compile the generated source file."""

    def __repr__(self) -> str:
        return self.script_name


"""Scripts under test.

When adding new generator scripts to the `scripts` directory,
do not forget to include them here.
"""
SCRIPTS = [
    ScriptInfo.make("Structural", ("h", "cpp")),
    ScriptInfo.make("SimpleJacobi", ("h", "cpp"), compilable_output="cpp"),
    ScriptInfo.make("SimpleClasses", ("h", "cpp")),
    ScriptInfo.make("Variables", ("h", "cpp"), compilable_output="cpp"),
]


@pytest.mark.parametrize("script_info", SCRIPTS)
def test_generator_script(script_info: ScriptInfo):
    """Test a generator script defined by ``script_info``.

    The generator script will be run, with its output placed in the ``out`` folder.
    If it is successful, its output files will be compared against
    any files of the same name from the ``expected`` folder.
    Finally, if any compilable files are specified, the test will attempt to compile them.
    """

    script_name = script_info.script_name
    script_file = path.join(SCRIPTS_DIR, script_name + ".py")

    output_dir = path.join(THIS_DIR, "out", script_name)
    if path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    args = ["python", script_file, "--sfg-output-dir", output_dir]

    result = subprocess.run(args)

    if result.returncode != 0:
        raise AssertionError(f"Generator script {script_name} failed.")

    #   Check generated files
    expected_files = set(
        [f"{script_name}.{ext}" for ext in script_info.expected_outputs]
    )
    output_files = set(os.listdir(output_dir))
    assert output_files == expected_files

    #   Check against expected output
    for ofile in output_files:
        expected_file = path.join(EXPECTED_DIR, ofile)
        actual_file = path.join(output_dir, ofile)

        if not path.exists(expected_file):
            continue

        with open(expected_file, "r") as f:
            expected = f.read()

        with open(actual_file, "r") as f:
            actual = f.read()

        #   Strip whitespace
        expected = "".join(expected.split())
        actual = "".join(actual.split())

        assert expected == actual

    #   Check if output compiles
    if (ext := script_info.compilable_output) is not None:
        compilable_file = f"{script_name}.{ext}"
        compile_args = script_info.compile_cmd.split() + ["-c", compilable_file]
        compile_result = subprocess.run(compile_args, cwd=output_dir)

        if compile_result.returncode != 0:
            raise AssertionError("Compilation of generated files failed.")
