from __future__ import annotations

from typing import Protocol

from .expressions import CppClass, cpptype, AugExpr


class Dim3Interface(CppClass):
    """Interface definition for the ``dim3`` struct of Cuda and HIP."""

    def ctor(self, dim0=1, dim1=1, dim2=1):
        """Constructor invocation of ``dim3``"""
        return self.ctor_bind(dim0, dim1, dim2)

    @property
    def x(self) -> AugExpr:
        """The `x` coordinate member."""
        return AugExpr.format("{}.x", self)

    @property
    def y(self) -> AugExpr:
        """The `y` coordinate member."""
        return AugExpr.format("{}.y", self)

    @property
    def z(self) -> AugExpr:
        """The `z` coordinate member."""
        return AugExpr.format("{}.z", self)

    @property
    def dims(self) -> tuple[AugExpr, AugExpr, AugExpr]:
        """`x`, `y`, and `z` as a tuple."""
        return (self.x, self.y, self.z)


class ProvidesGpuRuntimeAPI(Protocol):
    """Protocol definition for a GPU runtime API provider."""

    dim3: type[Dim3Interface]
    """The ``dim3`` struct type for this GPU runtime"""

    stream_t: type[AugExpr]
    """The ``stream_t`` type for this GPU runtime"""


class CudaAPI(ProvidesGpuRuntimeAPI):
    """Reflection of the CUDA runtime API"""

    class dim3(Dim3Interface):
        """Implements `Dim3Interface` for CUDA"""

        template = cpptype("dim3", "<cuda_runtime.h>")

    class stream_t(CppClass):
        template = cpptype("cudaStream_t", "<cuda_runtime.h>")


cuda = CudaAPI
"""Alias for `CudaAPI`"""


class HipAPI(ProvidesGpuRuntimeAPI):
    """Reflection of the HIP runtime API"""

    class dim3(Dim3Interface):
        """Implements `Dim3Interface` for HIP"""

        template = cpptype("dim3", "<hip/hip_runtime.h>")

    class stream_t(CppClass):
        template = cpptype("hipStream_t", "<hip/hip_runtime.h>")


hip = HipAPI
"""Alias for `HipAPI`"""
