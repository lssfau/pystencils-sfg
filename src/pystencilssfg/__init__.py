from .configuration import SfgConfiguration
from .generator import SourceFileGenerator
from .composer import SfgComposer

__all__ = [
    "SourceFileGenerator", "SfgComposer", "SfgConfiguration"
]

from . import _version
__version__ = _version.get_versions()['version']
