from os.path import dirname, realpath


def get_sfg_cmake_modulepath():
    return dirname(realpath(__file__))
