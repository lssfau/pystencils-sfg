from .configuration import SfgConfiguration
from .generator import SourceFileGenerator
from .composer import SfgComposer
from .context import SfgContext

__all__ = [
    "SourceFileGenerator", "SfgComposer", "SfgConfiguration", "SfgContext"
]

from . import _version
__version__ = _version.get_versions()['version']
