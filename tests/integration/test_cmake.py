import pytest

import pathlib
import subprocess

THIS_DIR = pathlib.Path(__file__).parent

CMAKE_PROJECT_DIRNAME = "cmake_project"
CMAKE_PROJECT_DIR = THIS_DIR / CMAKE_PROJECT_DIRNAME


@pytest.mark.parametrize(
    "config_source", [None, "UseGlobalCfgModule", "UseLocalCfgModule"]
)
def test_cmake_project(tmp_path, config_source):
    obtain_find_module_cmd = ["sfg-cli", "cmake", "make-find-module"]

    result = subprocess.run(obtain_find_module_cmd, cwd=CMAKE_PROJECT_DIR)
    assert result.returncode == 0

    cmake_configure_cmd = ["cmake", "-S", CMAKE_PROJECT_DIR, "-B", str(tmp_path)]
    if config_source is not None:
        cmake_configure_cmd.append(f"-D{config_source}=ON")
    configure_result = subprocess.run(cmake_configure_cmd)
    assert configure_result.returncode == 0

    cmake_build_cmd = ["cmake", "--build", str(tmp_path), "--target", "TestApp"]
    build_result = subprocess.run(cmake_build_cmd)
    assert build_result.returncode == 0

    run_cmd = [str(tmp_path / "TestApp")]
    run_result = subprocess.run(run_cmd)

    if config_source is not None:
        assert (tmp_path / "_gen" / "TestApp" / "gen" / "GenTest.c++").exists()
        assert run_result.returncode == 31
    else:
        assert (tmp_path / "_gen" / "TestApp" / "gen" / "GenTest.cpp").exists()
        assert run_result.returncode == 42

    cli_test_output = tmp_path / "_gen" / "TestApp" / "gen" / "CliTest.hpp"
    assert cli_test_output.exists()

    content = cli_test_output.read_text()
    assert 'arg0 = "apples";' in content
    assert 'arg1 = "bananas";' in content
    assert 'arg2 = "unicorns";' in content

    custom_dir_output = tmp_path / "my-output" / "CustomDirTest.hpp"
    assert custom_dir_output.exists()
    assert "#define NOTHING" in custom_dir_output.read_text()
