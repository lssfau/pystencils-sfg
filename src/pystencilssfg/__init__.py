from .configuration import SfgConfiguration, SfgOutputMode, SfgCodeStyle
from .generator import SourceFileGenerator
from .composer import SfgComposer
from .context import SfgContext
from .lang import SfgVar, AugExpr
from .exceptions import SfgException

__all__ = [
    "SourceFileGenerator",
    "SfgComposer",
    "SfgConfiguration",
    "SfgOutputMode",
    "SfgCodeStyle",
    "SfgContext",
    "SfgVar",
    "AugExpr",
    "SfgException",
]

from . import _version

__version__ = _version.get_versions()["version"]
