import ctypes
import threading
from contextlib import contextmanager

from django.contrib.gis.geos.base import GEOSBase
from django.contrib.gis.geos.error import GEOSException
from django.contrib.gis.geos.libgeos import (
    CONTEXT_PTR,
    error_h,
    geos_version_tuple,
    lgeos,
    notice_h,
)


class GEOSContextHandle(GEOSBase):
    """Represent a GEOS context handle."""

    ptr_type = CONTEXT_PTR
    destructor = lgeos.GEOS_finish_r

    def __init__(self):
        self.ptr = lgeos.GEOS_init_r()
        lgeos.GEOSContext_setNoticeHandler_r(self.ptr, notice_h)
        lgeos.GEOSContext_setErrorHandler_r(self.ptr, error_h)


# Defining a thread-local object and creating an instance
# to hold a reference to GEOSContextHandle for this thread.
class GEOSContext(threading.local):
    handle = None
    curve_to_line_params = None
    line_to_curve_params = None


thread_context = GEOSContext()


def _check_curve_conversion_support():
    if geos_version_tuple() < (3, 15, 0):
        raise GEOSException("Curve/line conversion requires GEOS >= 3.15.0.")


_curve_conversion_prototypes_configured = False


def _configure_curve_conversion_prototypes():
    # Lazily bind the GEOS 3.15.0+ curve/line conversion prototypes, so that
    # merely importing this module never touches symbols that don't exist in
    # older GEOS libraries.
    global _curve_conversion_prototypes_configured
    if _curve_conversion_prototypes_configured:
        return

    lgeos.GEOSCurveToLineParams_create.restype = ctypes.c_void_p
    lgeos.GEOSCurveToLineParams_setMaxStepDegrees_r.argtypes = [
        CONTEXT_PTR,
        ctypes.c_void_p,
        ctypes.c_double,
    ]
    lgeos.GEOSCurveToLineParams_setMaxDeviation_r.argtypes = [
        CONTEXT_PTR,
        ctypes.c_void_p,
        ctypes.c_double,
    ]
    lgeos.GEOSCurveToLineParams_destroy.argtypes = [ctypes.c_void_p]
    lgeos.GEOSLineToCurveParams_create.restype = ctypes.c_void_p
    lgeos.GEOSLineToCurveParams_destroy.argtypes = [ctypes.c_void_p]
    lgeos.GEOSLineToCurveParams_setRadiusTolerance_r.argtypes = [
        CONTEXT_PTR,
        ctypes.c_void_p,
        ctypes.c_double,
    ]
    lgeos.GEOSLineToCurveParams_setMaxStepDegrees_r.argtypes = [
        CONTEXT_PTR,
        ctypes.c_void_p,
        ctypes.c_double,
    ]
    lgeos.GEOSLineToCurveParams_setMaxAngleDifferenceDegrees_r.argtypes = [
        CONTEXT_PTR,
        ctypes.c_void_p,
        ctypes.c_double,
    ]
    lgeos.GEOSContext_setCurveToLineParams_r.argtypes = [CONTEXT_PTR, ctypes.c_void_p]
    lgeos.GEOSContext_setLineToCurveParams_r.argtypes = [CONTEXT_PTR, ctypes.c_void_p]

    _curve_conversion_prototypes_configured = True


class GEOSCurveToLineParams:
    """
    Parameters controlling how curved geometries are linearized by
    geos_curve_conversion(). Requires GEOS >= 3.15.0.
    """

    def __init__(self, max_step_degrees=None, max_deviation=None):
        _check_curve_conversion_support()
        _configure_curve_conversion_prototypes()
        thread_context.handle = thread_context.handle or GEOSContextHandle()
        self.ptr = lgeos.GEOSCurveToLineParams_create()

        if max_step_degrees is not None:
            lgeos.GEOSCurveToLineParams_setMaxStepDegrees_r(
                thread_context.handle.ptr, self.ptr, max_step_degrees
            )

        if max_deviation is not None:
            lgeos.GEOSCurveToLineParams_setMaxDeviation_r(
                thread_context.handle.ptr, self.ptr, max_deviation
            )

    def __del__(self):
        if hasattr(self, "ptr") and self.ptr:
            lgeos.GEOSCurveToLineParams_destroy(self.ptr)


class GEOSLineToCurveParams:
    """
    Parameters controlling how linearized geometries are converted back to
    curves by geos_curve_conversion(). Requires GEOS >= 3.15.0.
    """

    def __init__(
        self,
        radius_tolerance=None,
        max_step_degrees=None,
        max_angle_difference_degrees=None,
    ):
        _check_curve_conversion_support()
        _configure_curve_conversion_prototypes()
        thread_context.handle = thread_context.handle or GEOSContextHandle()
        self.ptr = lgeos.GEOSLineToCurveParams_create()

        if radius_tolerance is not None:
            lgeos.GEOSLineToCurveParams_setRadiusTolerance_r(
                thread_context.handle.ptr, self.ptr, radius_tolerance
            )

        if max_step_degrees is not None:
            lgeos.GEOSLineToCurveParams_setMaxStepDegrees_r(
                thread_context.handle.ptr, self.ptr, max_step_degrees
            )

        if max_angle_difference_degrees is not None:
            lgeos.GEOSLineToCurveParams_setMaxAngleDifferenceDegrees_r(
                thread_context.handle.ptr, self.ptr, max_angle_difference_degrees
            )

    def __del__(self):
        if hasattr(self, "ptr") and self.ptr:
            lgeos.GEOSLineToCurveParams_destroy(self.ptr)


@contextmanager
def geos_curve_conversion(curve_to_line_params=True, line_to_curve_params=True):
    """
    Context manager enabling automatic conversion between curved and linear
    geometries for the duration of the ``with`` block, for GEOS methods that
    don't support curved geometries. Requires GEOS >= 3.15.0.
    """
    _check_curve_conversion_support()
    _configure_curve_conversion_prototypes()
    thread_context.handle = thread_context.handle or GEOSContextHandle()
    prev_curve_to_line_params = thread_context.curve_to_line_params
    prev_line_to_curve_params = thread_context.line_to_curve_params

    if curve_to_line_params is True:
        curve_to_line_params = GEOSCurveToLineParams()
    if line_to_curve_params is True:
        line_to_curve_params = GEOSLineToCurveParams()

    try:
        # Set GEOSContext_setCurveToLineParams_r and
        # GEOSContext_setLineToCurveParams_r on the context.
        # This ensures that if a GEOS method does not support curves, it
        # will linearize any curve geometry input if needed, and will also
        # convert any linear output to a curved type, if the inputs were
        # converted to curves.
        lgeos.GEOSContext_setCurveToLineParams_r(
            thread_context.handle.ptr,
            curve_to_line_params.ptr if curve_to_line_params else None,
        )

        # Unless line_to_curve_params is provided, curves linearized via
        # curve_to_line_params will remain linear in the result, even if
        # the input geometries contained curves.
        lgeos.GEOSContext_setLineToCurveParams_r(
            thread_context.handle.ptr,
            line_to_curve_params.ptr if line_to_curve_params else None,
        )

        thread_context.curve_to_line_params = curve_to_line_params
        thread_context.line_to_curve_params = line_to_curve_params

        yield
    finally:
        lgeos.GEOSContext_setCurveToLineParams_r(
            thread_context.handle.ptr,
            prev_curve_to_line_params.ptr if prev_curve_to_line_params else None,
        )
        lgeos.GEOSContext_setLineToCurveParams_r(
            thread_context.handle.ptr,
            prev_line_to_curve_params.ptr if prev_line_to_curve_params else None,
        )
        thread_context.curve_to_line_params, thread_context.line_to_curve_params = (
            prev_curve_to_line_params,
            prev_line_to_curve_params,
        )


class GEOSFunc:
    """
    Serve as a wrapper for GEOS C Functions. Use thread-safe function
    variants when available.
    """

    def __init__(self, func_name):
        # GEOS thread-safe function signatures end with '_r' and take an
        # additional context handle parameter.
        self.cfunc = getattr(lgeos, func_name + "_r")
        # Create a reference to thread_context so it's not garbage-collected
        # before an attempt to call this object.
        self.thread_context = thread_context

    def __call__(self, *args):
        # Create a context handle if one doesn't exist for this thread.
        self.thread_context.handle = self.thread_context.handle or GEOSContextHandle()
        # Call the threaded GEOS routine with the pointer of the context handle
        # as the first argument.
        return self.cfunc(self.thread_context.handle.ptr, *args)

    def __str__(self):
        return self.cfunc.__name__

    # argtypes property
    def _get_argtypes(self):
        return self.cfunc.argtypes

    def _set_argtypes(self, argtypes):
        self.cfunc.argtypes = [CONTEXT_PTR, *argtypes]

    argtypes = property(_get_argtypes, _set_argtypes)

    # restype property
    def _get_restype(self):
        return self.cfunc.restype

    def _set_restype(self, restype):
        self.cfunc.restype = restype

    restype = property(_get_restype, _set_restype)

    # errcheck property
    def _get_errcheck(self):
        return self.cfunc.errcheck

    def _set_errcheck(self, errcheck):
        self.cfunc.errcheck = errcheck

    errcheck = property(_get_errcheck, _set_errcheck)
