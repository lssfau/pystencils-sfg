"""Test suite for generator scripts.

For more information, refer to the `README.md` file in the same directory.
"""

import pytest

import pathlib
import yaml
import re
import shutil
import warnings
import subprocess

from pystencils.include import get_pystencils_include_path

THIS_DIR = pathlib.Path(__file__).parent

DEPS_DIR = THIS_DIR / "deps"
MDSPAN_QUAL_PATH = "mdspan-mdspan-0.6.0/include/"

PYSTENCILS_RT_INCLUDE_PATH = get_pystencils_include_path()

TEST_INDEX = THIS_DIR / "index.yaml"
SOURCE_DIR = THIS_DIR / "source"
EXPECTED_DIR = THIS_DIR / "expected"
CXX_INCLUDE_FLAGS = [
    "-I",
    f"{DEPS_DIR}/{MDSPAN_QUAL_PATH}",
    "-I",
    PYSTENCILS_RT_INCLUDE_PATH,
]


def prepare_deps():
    mdspan_archive_url = (
        "https://github.com/kokkos/mdspan/archive/refs/tags/mdspan-0.6.0.zip"
    )
    mdspan_path = DEPS_DIR / MDSPAN_QUAL_PATH

    import fasteners

    with fasteners.InterProcessLock(THIS_DIR / ".get-deps.lock"):
        if not mdspan_path.exists():
            DEPS_DIR.mkdir(parents=True, exist_ok=True)
            print("Downloading mdspan reference implementation...")

            import requests
            import tempfile
            from zipfile import ZipFile

            server_resp = requests.get(mdspan_archive_url)
            with tempfile.TemporaryFile() as tmpfile:
                tmpfile.write(server_resp.content)

                with ZipFile(tmpfile) as archive:
                    for name in archive.namelist():
                        if name.startswith(MDSPAN_QUAL_PATH):
                            archive.extract(name, DEPS_DIR)


class GenScriptTest:
    @classmethod
    def make(cls, name, test_description: dict):
        return pytest.param(cls(name, test_description), id=f"{name}.py")

    def __init__(self, name: str, test_description: dict):
        self._name = name
        script_path = SOURCE_DIR / f"{name}.py"

        if not script_path.exists():
            raise ValueError(f"Script {script_path.name} does not exist.")

        self._script_path = script_path

        self._output_dir: pathlib.Path
        self._script_args = []

        expected_extensions = ["cpp", "hpp"]

        sfg_args: dict = test_description.get("sfg-args", dict())

        if (header_only := sfg_args.get("header-only", None)) is not None:
            if header_only:
                expected_extensions = ["hpp"]
                self._script_args += ["--sfg-header-only"]
            else:
                self._script_args += ["--no--sfg-header-only"]

        if (file_exts := sfg_args.get("file-extensions", None)) is not None:
            expected_extensions = file_exts
            self._script_args += ["--sfg-file-extensions", ",".join(file_exts)]

        if (config_module := sfg_args.get("config-module", None)) is not None:
            config_module = SOURCE_DIR / config_module
            self._script_args += ["--sfg-config-module", str(config_module)]

        self._script_args += test_description.get("extra-args", [])

        self._expected_extensions = test_description.get(
            "expected-output", expected_extensions
        )

        self._expect_failure = test_description.get("expect-failure", False)

        self._expected_files: set[str] = set()
        self._files_to_compile: list[str] = []

        for ext in self._expected_extensions:
            fname = f"{self._name}.{ext}"
            self._expected_files.add(fname)
            if ext in ("cpp", "cxx", "c++", "cu", "hip"):
                self._files_to_compile.append(fname)

        compile_descr: dict = test_description.get("compile", dict())
        cxx_compiler: str = compile_descr.get("cxx", "g++")

        skip_if_no_compiler: bool = compile_descr.get("skip-if-not-found", False)
        cxx_options: list[str] = compile_descr.get(
            "cxx-flags", ["--std=c++20", "-Wall", "-Werror"]
        )
        link_options: list[str] = compile_descr.get("link-flags", [])

        self._compile_cmd: list[str] | None
        self._link_cmd: list[str] | None

        if shutil.which(cxx_compiler) is None:
            if skip_if_no_compiler:
                warnings.warn(
                    f"[Test/{self._name}] Requested compiler {cxx_compiler} is not available."
                )
                self._compile_cmd = self._link_cmd = None
            else:
                pytest.fail(f"Requested compiler {cxx_compiler} is not available.")
        else:
            self._compile_cmd = (
                [cxx_compiler] + cxx_options + CXX_INCLUDE_FLAGS + ["-c"]
            )
            self._link_cmd = [cxx_compiler] + link_options

        self._expect_code: dict = test_description.get("expect-code", dict())

        harness_file = SOURCE_DIR / f"{self._name}.harness.cpp"
        if harness_file.exists():
            self._harness = harness_file
        else:
            self._harness = None

    def run(self, output_dir: pathlib.Path):
        self._output_dir = output_dir

        self.run_script()

        if self._expect_failure:
            return

        self.check_output_files()
        self.compile_files()
        self.run_harness()

    def run_script(self):
        args = [
            "python",
            str(self._script_path),
            "--sfg-output-dir",
            str(self._output_dir),
        ] + list(self._script_args)
        result = subprocess.run(args)

        if self._expect_failure:
            if result.returncode == 0:
                pytest.fail(
                    f"Generator script {self._script_path.name} was expected to fail, but didn't."
                )
        elif result.returncode != 0:
            pytest.fail(f"Generator script {self._script_path.name} failed.")

    def check_output_files(self):
        output_files = set(p.name for p in self._output_dir.iterdir())
        assert output_files == self._expected_files

        for fp in self._output_dir.iterdir():
            self.check_file(fp)

    def check_file(self, actual_file: pathlib.Path):
        with actual_file.open("r") as f:
            actual_code = f.read()

        extension = actual_file.name.split(".")[1]
        if (expectations := self._expect_code.get(extension, None)) is not None:
            for expectation in expectations:
                if isinstance(expectation, str):
                    assert (
                        expectation in actual_code
                    ), f"Did not find expected code string in contents of {actual_file.name}:\n{expectation}"
                elif isinstance(expectation, dict):
                    if (regex := expectation.get("regex", None)) is not None:
                        if expectation.get("strip-whitespace", False):
                            regex = "".join(regex.split())
                        matcher = re.compile(regex)
                        count = expectation.get("count", 1)
                        findings = matcher.findall(actual_code)
                        assert len(findings) == count, (
                            f"Regex {regex} matched incorrect number of times in generated code in {actual_file.name}:"
                            f"\nExpected {count}, got {len(findings)}"
                        )

    def compile_files(self):
        if self._compile_cmd is None:
            return

        #   Check if output compiles
        for file in self._files_to_compile:
            compile_args = self._compile_cmd + [file]
            compile_result = subprocess.run(compile_args, cwd=str(self._output_dir))

            if compile_result.returncode != 0:
                cmd_str = " ".join(compile_args)
                pytest.fail(
                    "Compilation of generated files failed: \n"
                    f"    Command: {cmd_str}"
                )

        if self._harness is not None:
            compile_args = self._compile_cmd + [
                "-I",
                str(self._output_dir),
                str(self._harness),
            ]
            compile_result = subprocess.run(compile_args, cwd=str(self._output_dir))

            if compile_result.returncode != 0:
                pytest.fail(f"Compilation of test harness for {self._name} failed.")

    def run_harness(self):
        if self._compile_cmd is None:
            return

        #   Run after `compile`; i.e. for all compilable generated files, objects are already present
        if self._harness is not None:
            objects = self._output_dir.glob("*.o")
            linker_args = self._link_cmd + [str(obj) for obj in objects]
            linker_result = subprocess.run(linker_args, cwd=str(self._output_dir))

            if linker_result.returncode != 0:
                pytest.fail(f"Linking to test harness for {self._name} failed.")

            exe_args = "./a.out"
            exe_result = subprocess.run(exe_args, cwd=str(self._output_dir))
            if exe_result.returncode != 0:
                pytest.fail(f"Execution of test harness for {self._name} failed.")


def discover() -> list[GenScriptTest]:
    with TEST_INDEX.open() as indexfile:
        index = yaml.safe_load(indexfile.read())

    tests = []
    for name, descr in index.items():
        if descr is None:
            descr = dict()
        tests.append(GenScriptTest.make(name, descr))
    return tests


DISCOVERED_TESTS = discover()


@pytest.mark.parametrize("test_descriptor", DISCOVERED_TESTS)
def test_generator_script(test_descriptor: GenScriptTest, tmp_path):
    prepare_deps()
    test_descriptor.run(tmp_path)
