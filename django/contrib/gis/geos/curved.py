"""
This module houses the curved GEOS geometry types: CircularString,
CompoundCurve, CurvePolygon, MultiCurve, and MultiSurface.

These types require GEOS >= 3.13, which introduced container support
(construction and WKB serialization) for curved geometries. Spatial
algorithms (e.g. area, length, intersection) are not available for
curved types.
"""

from django.contrib.gis.geos import prototypes as capi
from django.contrib.gis.geos.collections import GeometryCollection
from django.contrib.gis.geos.error import GEOSException
from django.contrib.gis.geos.geometry import GEOSGeometry
from django.contrib.gis.geos.libgeos import GEOM_PTR, geos_version_tuple
from django.contrib.gis.geos.linestring import LinearRing, LineString
from django.contrib.gis.geos.polygon import Polygon


def _check_curved_support():
    if geos_version_tuple() < (3, 13, 0):
        raise GEOSException(
            "Curved geometry types require GEOS >= 3.13.0. "
            "The installed GEOS version is %s.%s.%s." % geos_version_tuple()
        )


class CircularString(LineString):
    """
    A GEOS CircularString geometry. Requires GEOS >= 3.13.

    A circular string is defined by sequences of three points where the
    middle point lies on the arc. Each consecutive arc shares its start
    point with the end of the previous arc, so (n-1)/2 arcs are defined
    for n points (n must be odd and >= 3).

    Example:
     >>> from django.contrib.gis.geos import CircularString
     >>> cs = CircularString((0, 0), (1, 1), (2, 0))
    """

    _init_func = capi.create_circularstring
    _minlength = 3

    def __init__(self, *args, **kwargs):
        _check_curved_support()
        if not args:
            srid = kwargs.get("srid")
            GEOSGeometry.__init__(self, capi.create_empty_circularstring(), srid=srid)
        else:
            LineString.__init__(self, *args, **kwargs)


class CompoundCurve(GeometryCollection):
    """
    A GEOS CompoundCurve geometry. Requires GEOS >= 3.13.

    A compound curve is a contiguous sequence of LineStrings and/or
    CircularStrings. Adjacent components must share their endpoints.

    Example:
     >>> from django.contrib.gis.geos import CompoundCurve, LineString
     >>> cc = CompoundCurve(
     ...     LineString((0, 0), (1, 0)),
     ...     CircularString((1, 0), (2, 1), (3, 0)),
     ... )
    """

    _typeid = 9

    def __init__(self, *args, **kwargs):
        _check_curved_support()
        super().__init__(*args, **kwargs)

    def _create_collection(self, length, items):
        if not length:
            return capi.create_empty_compoundcurve()
        geoms = (GEOM_PTR * length)(
            *[capi.geom_clone(getattr(g, "ptr", g)) for g in items]
        )
        return capi.create_compoundcurve(geoms, length)


class CurvePolygon(Polygon):
    """
    A GEOS CurvePolygon geometry. Requires GEOS >= 3.13.

    A curve polygon is like a polygon, but its rings may be LinearRings,
    CircularStrings, or CompoundCurves.

    Example:
     >>> from django.contrib.gis.geos import CurvePolygon
     >>> cp = CurvePolygon(
     ...     CircularString((0, 0), (1, 1), (2, 0), (1, -1), (0, 0))
     ... )
    """

    def __init__(self, *args, **kwargs):
        _check_curved_support()
        super().__init__(*args, **kwargs)

    def _construct_ring(self, param, msg=None):
        "Accept LinearRing, CircularString, or CompoundCurve as rings."
        if isinstance(param, (LinearRing, CircularString, CompoundCurve, LineString)):
            return param
        # Fall back to constructing a LinearRing for coordinate sequences.
        try:
            return LinearRing(param)
        except TypeError:
            raise TypeError(
                "Parameter must be a LinearRing, CircularString, CompoundCurve, "
                "or a sequence that can initialize to a LinearRing."
            )

    def _create_polygon(self, length, items):
        if not length:
            return capi.create_empty_curvepolygon()

        rings = []
        for r in items:
            if isinstance(r, GEOM_PTR):
                rings.append(r)
            else:
                rings.append(self._construct_ring(r))

        shell = self._clone(rings.pop(0))

        n_holes = length - 1
        if n_holes:
            holes_param = (GEOM_PTR * n_holes)(*[self._clone(r) for r in rings])
        else:
            holes_param = None

        return capi.create_curvepolygon(shell, holes_param, n_holes)


class MultiCurve(GeometryCollection):
    """
    A GEOS MultiCurve geometry. Requires GEOS >= 3.13.

    A homogeneous collection of curves: LineStrings, CircularStrings,
    or CompoundCurves.
    """

    _typeid = 11

    def __init__(self, *args, **kwargs):
        _check_curved_support()
        super().__init__(*args, **kwargs)


class MultiSurface(GeometryCollection):
    """
    A GEOS MultiSurface geometry. Requires GEOS >= 3.13.

    A homogeneous collection of surfaces: Polygons or CurvePolygons.
    """

    _typeid = 12

    def __init__(self, *args, **kwargs):
        _check_curved_support()
        super().__init__(*args, **kwargs)


# Set allowed component types after all classes are defined.
CompoundCurve._allowed = (LineString, LinearRing, CircularString)
MultiCurve._allowed = (LineString, LinearRing, CircularString, CompoundCurve)
MultiSurface._allowed = (Polygon, CurvePolygon)
