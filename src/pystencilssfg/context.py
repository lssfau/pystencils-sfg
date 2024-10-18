from typing import Generator, Sequence, Any

from .configuration import SfgCodeStyle
from .ir.source_components import (
    SfgHeaderInclude,
    SfgKernelNamespace,
    SfgFunction,
    SfgClass,
)
from .exceptions import SfgException


class SfgContext:
    """Represents a header/implementation file pair in the code generator.

    **Source File Properties and Components**

    The SfgContext collects all properties and components of a header/implementation
    file pair (or just the header file, if header-only generation is used).
    These are:

    - The code namespace, which is combined from the `outer_namespace`
      and the `pystencilssfg.SfgContext.inner_namespace`. The outer namespace is meant to be set
      externally e.g. by the project configuration, while the inner namespace is meant to be set by the generator
      script.
    - The `prelude comment` is a block of text printed as a comment block
      at the top of both generated files. Typically, it contains authorship and licence information.
    - The set of included header files (`pystencilssfg.SfgContext.includes`).
    - Custom `definitions`, which are just arbitrary code strings.
    - Any number of kernel namespaces (`pystencilssfg.SfgContext.kernel_namespaces`), within which *pystencils*
      kernels are managed.
    - Any number of functions (`pystencilssfg.SfgContext.functions`), which are meant to serve as wrappers
      around kernel calls.
    - Any number of classes (`pystencilssfg.SfgContext.classes`), which can be used to build more extensive wrappers
      around kernels.

    **Order of Definitions**

    To honor C/C++ use-after-declare rules, the context preserves the order in which definitions, functions and classes
    are added to it.
    The header file printers implemented in *pystencils-sfg* will print the declarations accordingly.
    The declarations can retrieved in order of definition via `declarations_ordered`.
    """

    def __init__(
        self,
        outer_namespace: str | None = None,
        codestyle: SfgCodeStyle = SfgCodeStyle(),
        argv: Sequence[str] | None = None,
        project_info: Any = None,
    ):
        """
        Args:
            outer_namespace: Qualified name of the outer code namespace
            codestyle: Code style that should be used by the code emitter
            argv: The generator script's command line arguments.
                Reserved for internal use by the [SourceFileGenerator][pystencilssfg.SourceFileGenerator].
            project_info: Project-specific information provided by a build system.
                Reserved for internal use by the [SourceFileGenerator][pystencilssfg.SourceFileGenerator].
        """
        self._argv = argv
        self._project_info = project_info
        self._default_kernel_namespace = SfgKernelNamespace(self, "kernels")

        self._outer_namespace = outer_namespace
        self._inner_namespace: str | None = None

        self._codestyle = codestyle

        #   Source Components
        self._prelude: str = ""
        self._includes: list[SfgHeaderInclude] = []
        self._definitions: list[str] = []
        self._kernel_namespaces = {
            self._default_kernel_namespace.name: self._default_kernel_namespace
        }
        self._functions: dict[str, SfgFunction] = dict()
        self._classes: dict[str, SfgClass] = dict()

        self._declarations_ordered: list[str | SfgFunction | SfgClass] = list()

    @property
    def argv(self) -> Sequence[str]:
        """If this context was created by a `pystencilssfg.SourceFileGenerator`, provides the command
        line arguments given to the generator script, with configuration arguments for the code generator
        stripped away.

        Otherwise, throws an exception."""
        if self._argv is None:
            raise SfgException("This context provides no command-line arguments.")
        return self._argv

    @property
    def project_info(self) -> Any:
        """Project-specific information provided by a build system."""
        return self._project_info

    @property
    def outer_namespace(self) -> str | None:
        """Outer code namespace. Set by constructor argument `outer_namespace`."""
        return self._outer_namespace

    @property
    def inner_namespace(self) -> str | None:
        """Inner code namespace. Set by `set_namespace`."""
        return self._inner_namespace

    @property
    def fully_qualified_namespace(self) -> str | None:
        """Combined outer and inner namespaces, as `outer_namespace::inner_namespace`."""
        match (self.outer_namespace, self.inner_namespace):
            case None, None:
                return None
            case outer, None:
                return outer
            case None, inner:
                return inner
            case outer, inner:
                return f"{outer}::{inner}"
            case _:
                assert False

    @property
    def codestyle(self) -> SfgCodeStyle:
        """The code style object for this generation context."""
        return self._codestyle

    # ----------------------------------------------------------------------------------------------
    #   Prelude, Includes, Definitions, Namespace
    # ----------------------------------------------------------------------------------------------

    @property
    def prelude_comment(self) -> str:
        """The prelude is a comment block printed at the top of both generated files."""
        return self._prelude

    def append_to_prelude(self, code_str: str):
        """Append a string to the prelude comment.

        The string should not contain
        C/C++ comment delimiters, since these will be added automatically during
        code generation.
        """
        if self._prelude:
            self._prelude += "\n"

        self._prelude += code_str

        if not code_str.endswith("\n"):
            self._prelude += "\n"

    def includes(self) -> Generator[SfgHeaderInclude, None, None]:
        """Includes of headers. Public includes are added to the header file, private includes
        are added to the implementation file."""
        yield from self._includes

    def add_include(self, include: SfgHeaderInclude):
        self._includes.append(include)

    def definitions(self) -> Generator[str, None, None]:
        """Definitions are arbitrary custom lines of code."""
        yield from self._definitions

    def add_definition(self, definition: str):
        """Add a custom code string to the header file."""
        self._definitions.append(definition)
        self._declarations_ordered.append(definition)

    def set_namespace(self, namespace: str):
        """Set the inner code namespace.

        Throws an exception if the namespace was already set.
        """
        if self._inner_namespace is not None:
            raise SfgException("The code namespace was already set.")

        self._inner_namespace = namespace

    # ----------------------------------------------------------------------------------------------
    #   Kernel Namespaces
    # ----------------------------------------------------------------------------------------------

    @property
    def default_kernel_namespace(self) -> SfgKernelNamespace:
        """The default kernel namespace."""
        return self._default_kernel_namespace

    def kernel_namespaces(self) -> Generator[SfgKernelNamespace, None, None]:
        """Iterator over all registered kernel namespaces."""
        yield from self._kernel_namespaces.values()

    def get_kernel_namespace(self, str) -> SfgKernelNamespace | None:
        """Retrieve a kernel namespace by name, or `None` if it does not exist."""
        return self._kernel_namespaces.get(str)

    def add_kernel_namespace(self, namespace: SfgKernelNamespace):
        """Adds a new kernel namespace.

        If a kernel namespace of the same name already exists, throws an exception.
        """
        if namespace.name in self._kernel_namespaces:
            raise ValueError(f"Duplicate kernel namespace: {namespace.name}")

        self._kernel_namespaces[namespace.name] = namespace

    # ----------------------------------------------------------------------------------------------
    #   Functions
    # ----------------------------------------------------------------------------------------------

    def functions(self) -> Generator[SfgFunction, None, None]:
        """Iterator over all registered functions."""
        yield from self._functions.values()

    def get_function(self, name: str) -> SfgFunction | None:
        """Retrieve a function by name. Returns `None` if no function of the given name exists."""
        return self._functions.get(name, None)

    def add_function(self, func: SfgFunction):
        """Adds a new function.

        If a function or class with the same name exists already, throws an exception.
        """
        if func.name in self._functions or func.name in self._classes:
            raise SfgException(f"Duplicate function: {func.name}")

        self._functions[func.name] = func
        self._declarations_ordered.append(func)

    # ----------------------------------------------------------------------------------------------
    #   Classes
    # ----------------------------------------------------------------------------------------------

    def classes(self) -> Generator[SfgClass, None, None]:
        """Iterator over all registered classes."""
        yield from self._classes.values()

    def get_class(self, name: str) -> SfgClass | None:
        """Retrieve a class by name, or `None` if the class does not exist."""
        return self._classes.get(name, None)

    def add_class(self, cls: SfgClass):
        """Add a class.

        Throws an exception if a class or function of the same name exists already.
        """
        if cls.class_name in self._classes or cls.class_name in self._functions:
            raise SfgException(f"Duplicate class: {cls.class_name}")

        self._classes[cls.class_name] = cls
        self._declarations_ordered.append(cls)

    # ----------------------------------------------------------------------------------------------
    #   Declarations in order of addition
    # ----------------------------------------------------------------------------------------------

    def declarations_ordered(
        self,
    ) -> Generator[str | SfgFunction | SfgClass, None, None]:
        """All declared definitions, classes and functions in the order they were added.

        Awareness about order is necessary due to the C++ declare-before-use rules."""
        yield from self._declarations_ordered
