import threading
from ctypes import c_void_p

from django.contrib.gis.geos.base import GEOSBase
from django.contrib.gis.geos.libgeos import (
    CONTEXT_PTR,
    error_h,
    geos_version_tuple,
    lgeos,
    notice_h,
)
from django.core.exceptions import ImproperlyConfigured


class GEOSContextHandle(GEOSBase):
    """Represent a GEOS context handle."""

    ptr_type = CONTEXT_PTR
    destructor = lgeos.GEOS_finish_r

    def __init__(self):
        self.ptr = lgeos.GEOS_init_r()
        lgeos.GEOSContext_setNoticeHandler_r(self.ptr, notice_h)
        lgeos.GEOSContext_setErrorHandler_r(self.ptr, error_h)

        # GEOS 3.15.0+ introduces the CurveToLine/LineToCurve conversion.
        if geos_version_tuple() >= (3, 15, 0):
            try:
                from django.conf import settings

                convert_curve_to_line = settings.GEOS_CURVE_TO_LINE
            except (AttributeError, ImportError, ImproperlyConfigured, OSError):
                convert_curve_to_line = False

            try:
                from django.conf import settings

                convert_line_to_curve = settings.GEOS_LINE_TO_CURVE

                if not convert_curve_to_line and convert_line_to_curve:
                    raise ImproperlyConfigured(
                        "GEOS_LINE_TO_CURVE cannot be enabled if "
                        "GEOS_CURVE_TO_LINE is disabled."
                    )
            except (AttributeError, ImportError, ImproperlyConfigured, OSError):
                convert_line_to_curve = False
        else:
            convert_curve_to_line = False
            convert_line_to_curve = False

        # Set setCurveToLineParams_r and setLineToCurveParams with default
        # params to the context.
        # This ensures that if a GEOS method does not support curves, it will
        # linearize any curve geometry input if needed, and will also convert
        # any linear output to a curved type, if the inputs were converted to
        # curves.
        if convert_curve_to_line:
            lgeos.GEOSCurveToLineParams_create.restype = c_void_p
            lgeos.GEOSContext_setCurveToLineParams_r.argtypes = [CONTEXT_PTR, c_void_p]
            lgeos.GEOSCurveToLineParams_destroy.argtypes = [c_void_p]

            curveToLineParams = lgeos.GEOSCurveToLineParams_create()
            lgeos.GEOSContext_setCurveToLineParams_r(self.ptr, curveToLineParams)
            lgeos.GEOSCurveToLineParams_destroy(curveToLineParams)

            # Unless we set GEOS_CURVE_TO_LINE to True, curves will stay linear
            # in the result of the function, even if the input geometries
            # contain curves.
            if convert_line_to_curve:
                lgeos.GEOSLineToCurveParams_create.restype = c_void_p
                lgeos.GEOSContext_setLineToCurveParams_r.argtypes = [
                    CONTEXT_PTR,
                    c_void_p,
                ]
                lgeos.GEOSLineToCurveParams_destroy.argtypes = [c_void_p]

                lineToCurveParams = lgeos.GEOSLineToCurveParams_create()
                lgeos.GEOSContext_setLineToCurveParams_r(self.ptr, lineToCurveParams)
                lgeos.GEOSLineToCurveParams_destroy(lineToCurveParams)


# Defining a thread-local object and creating an instance
# to hold a reference to GEOSContextHandle for this thread.
class GEOSContext(threading.local):
    handle = None


thread_context = GEOSContext()


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
