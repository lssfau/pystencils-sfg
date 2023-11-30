from sys import stderr
from pystencilssfg import SfgConfiguration

def sfg_config():
    print("sfg_config() called!", file=stderr)

    project_info = {
        'B': 'A'
    }

    return SfgConfiguration(
        header_extension='hpp',
        source_extension='cpp',
        outer_namespace='cmake_demo',
        project_info=project_info
    )
