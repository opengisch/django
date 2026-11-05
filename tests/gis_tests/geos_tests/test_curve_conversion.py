import ctypes
from unittest import skipIf

from django.contrib.gis.geos import (
    CircularString,
    GEOSCurveToLineParams,
    GEOSException,
    geos_curve_conversion,
)
from django.contrib.gis.geos.libgeos import (
    CONTEXT_PTR,
    GEOM_PTR,
    geos_version_tuple,
    lgeos,
)
from django.test import SimpleTestCase


@skipIf(
    geos_version_tuple() < (3, 15, 0),
    "geos_curve_conversion requires GEOS 3.15.0 and later.",
)
class CurveConversionTests(SimpleTestCase):
    def setUp(self):
        from django.contrib.gis.geos.prototypes import threadsafe

        self.threadsafe = threadsafe

    def _get_circular_string(self):
        return CircularString((0, 0), (5, 5), (10, 0), (5, -5), (0, 0))

    def test_context_prevents_exceptions(self):
        # Curved-geometry predicates aren't supported by GEOS outside of a
        # geos_curve_conversion() block.
        with self.assertRaises(GEOSException):
            self._get_circular_string().equals(self._get_circular_string())

        with geos_curve_conversion():
            self.assertTrue(
                self._get_circular_string().equals(self._get_circular_string())
            )

    def test_curve_to_line_disable_conversion(self):
        with geos_curve_conversion(curve_to_line_params=None):
            with self.assertRaises(GEOSException):
                self._get_circular_string().equals(self._get_circular_string())

    def test_restores_previous_state_on_exit(self):
        with self.assertRaises(GEOSException):
            self._get_circular_string().equals(self._get_circular_string())

        with geos_curve_conversion():
            self._get_circular_string().equals(self._get_circular_string())

        with self.assertRaises(GEOSException):
            self._get_circular_string().equals(self._get_circular_string())

        with self.assertRaises(ValueError):
            with geos_curve_conversion():
                raise ValueError("boom")

        with self.assertRaises(GEOSException):
            self._get_circular_string().equals(self._get_circular_string())

    def test_max_step_degrees_changes_linearization(self):
        # A regression test for the params object actually reaching GEOS:
        # equals() succeeding only proves *some* conversion happened, not
        # that the requested tolerance was applied. Count the coordinates
        # GEOSCurveToLine_r actually produces for two different tolerances.
        lgeos.GEOSCurveToLine_r.restype = GEOM_PTR
        lgeos.GEOSCurveToLine_r.argtypes = [CONTEXT_PTR, GEOM_PTR, ctypes.c_void_p]
        lgeos.GEOSGetNumCoordinates_r.restype = ctypes.c_int
        lgeos.GEOSGetNumCoordinates_r.argtypes = [CONTEXT_PTR, GEOM_PTR]

        geom = self._get_circular_string()
        ctx = self.threadsafe.thread_context.handle.ptr

        coarse = GEOSCurveToLineParams(max_step_degrees=90.0)
        fine = GEOSCurveToLineParams(max_step_degrees=5.0)

        coarse_line = lgeos.GEOSCurveToLine_r(ctx, geom.ptr, coarse.ptr)
        fine_line = lgeos.GEOSCurveToLine_r(ctx, geom.ptr, fine.ptr)

        coarse_coords = lgeos.GEOSGetNumCoordinates_r(ctx, coarse_line)
        fine_coords = lgeos.GEOSGetNumCoordinates_r(ctx, fine_line)

        self.assertLess(coarse_coords, fine_coords)
