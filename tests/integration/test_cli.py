import subprocess


def test_list_files():
    output_dir = "/my/output/directory"
    args = [
        "sfg-cli",
        "list-files",
        "--sfg-output-dir",
        output_dir,
        "--sfg-file-extensions",
        "cu, cuh",
        "genscript.py",
    ]

    result = subprocess.run(args, capture_output=True, text=True)

    assert result.returncode == 0
    assert (
        result.stdout
        == "/my/output/directory/genscript.cuh /my/output/directory/genscript.cu\n"
    )


def test_list_files_headeronly():
    output_dir = "/my/output/directory"
    args = [
        "python", "-m", "pystencilssfg",
        "list-files",
        "--sfg-output-dir",
        output_dir,
        "--sfg-output-mode",
        "header-only",
        "genscript.py",
    ]

    result = subprocess.run(args, capture_output=True, text=True)

    assert result.returncode == 0
    assert result.stdout == "/my/output/directory/genscript.hpp\n"


def test_list_files_with_config_module(sample_config_module):
    args = [
        "sfg-cli",
        "list-files",
        "--sfg-config-module",
        sample_config_module,
        "genscript.py",
    ]

    result = subprocess.run(args, capture_output=True, text=True)

    assert result.returncode == 0
    assert (
        result.stdout
        == "generated_sources/genscript.hpp generated_sources/genscript.cpp\n"
    )


def test_make_find_module(tmp_path):
    args = ["sfg-cli", "cmake", "make-find-module"]

    result = subprocess.run(args, cwd=str(tmp_path))
    assert result.returncode == 0

    expected_path = tmp_path / "FindPystencilsSfg.cmake"
    assert expected_path.exists()
