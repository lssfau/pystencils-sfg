from pystencilssfg import lang


def dim3class(gpu_runtime_header: str, *, cls_name: str = "dim3"):
    """
    >>> dim3 = dim3class("<hip/hip_runtime.h>")
    >>> dim3().ctor(64, 1, 1)
    dim3{64, 1, 1}

    Args:
        gpu_runtime_header: String with the name of the gpu runtime header
        cls_name: String with the acutal name (default "dim3")
    Returns:
        Dim3Class: A `lang.CppClass` that mimics cuda's/hip's `dim3`
    """
    @lang.cppclass(cls_name, gpu_runtime_header)
    class Dim3Class:
        def ctor(self, dim0=1, dim1=1, dim2=1):
            return self.ctor_bind(dim0, dim1, dim2)

        @property
        def x(self):
            return lang.AugExpr.format("{}.x", self)

        @property
        def y(self):
            return lang.AugExpr.format("{}.y", self)

        @property
        def z(self):
            return lang.AugExpr.format("{}.z", self)

        @property
        def dims(self):
            """The dims property."""
            return [self.x, self.y, self.z]

    return Dim3Class
