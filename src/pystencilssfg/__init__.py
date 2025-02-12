from .config import SfgConfig, GLOBAL_NAMESPACE, OutputMode
from .generator import SourceFileGenerator
from .composer import SfgComposer
from .context import SfgContext
from .lang import SfgVar, AugExpr
from .exceptions import SfgException

__all__ = [
    "SfgConfig",
    "GLOBAL_NAMESPACE",
    "OutputMode",
    "SourceFileGenerator",
    "SfgComposer",
    "SfgContext",
    "SfgVar",
    "AugExpr",
    "SfgException",
]

from . import _version

__version__ = _version.get_versions()["version"]
