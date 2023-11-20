from os.path import dirname, realpath, join
import shutil


def get_sfg_cmake_modulepath():
    return join(dirname(realpath(__file__)), "modules")


def make_find_module():
    cmake_dir = dirname(realpath(__file__))
    find_module_file = join(cmake_dir, "FindPystencilsSfg.cmake")
    shutil.copy(find_module_file, "FindPystencilsSfg.cmake")
