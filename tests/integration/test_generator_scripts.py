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
    script_name: str
    expected_outputs: tuple[str, ...]

    compilable_output: str | None = None
    compile_cmd: str = f"g++ --std=c++17 -I {THIS_DIR}/deps/mdspan/include"


SCRIPTS = [
    ScriptInfo("SimpleJacobi", ("h", "cpp"), compilable_output="cpp"),
    ScriptInfo("SimpleClasses", ("h", "cpp")),
]


@pytest.mark.parametrize("script_info", SCRIPTS)
def test_generator_script(script_info: ScriptInfo):
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
        actual = "".join(expected.split())

        assert expected == actual

    #   Check if output compiles
    if (ext := script_info.compilable_output) is not None:
        compilable_file = f"{script_name}.{ext}"
        compile_args = script_info.compile_cmd.split() + ["-c", compilable_file]
        compile_result = subprocess.run(compile_args, cwd=output_dir)

        if compile_result.returncode != 0:
            raise AssertionError("Compilation of generated files failed.")
