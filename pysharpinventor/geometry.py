#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    pysharpinventor.geometry
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Casting helpers for B-Rep geometry. ``Edge.Geometry`` and
    ``Face.Geometry`` come back as a bare ``System.__ComObject``; these
    helpers cast it to the matching Inventor class (``LineSegment``,
    ``Circle``, ``Plane``, ``Cylinder``, ...).

    :copyright: (c) 2026
    :license: BSD, see LICENSE.txt for more details.
"""

import logging

from pysharpinventor._interop import InventorInterop, register_extension

__all__ = ['get_edge_curve_type', 'cast_edge_geometry',
           'get_face_surface_type', 'cast_face_geometry']

logger = logging.getLogger(__name__)

# CurveTypeEnum member name -> Inventor geometry class name
_CURVE_TYPE_CLASS_NAMES = {
    'kLineCurve': 'Line',
    'kLineSegmentCurve': 'LineSegment',
    'kCircleCurve': 'Circle',
    'kCircularArcCurve': 'Arc3d',
    'kEllipseFullCurve': 'EllipseFull',
    'kEllipticalArcCurve': 'EllipticalArc',
    'kBSplineCurve': 'BSplineCurve',
    'kPolylineCurve': 'Polyline3d',
}

# SurfaceTypeEnum member name -> Inventor geometry class name
_SURFACE_TYPE_CLASS_NAMES = {
    'kPlaneSurface': 'Plane',
    'kCylinderSurface': 'Cylinder',
    'kEllipticalCylinderSurface': 'EllipticalCylinder',
    'kConeSurface': 'Cone',
    'kEllipticalConeSurface': 'EllipticalCone',
    'kTorusSurface': 'Torus',
    'kSphereSurface': 'Sphere',
    'kBSplineSurface': 'BSplineSurface',
}

# Enum name -> {enum value: class}, built on first use (needs the Interop DLL)
_type_classes = {}


def _get_type_classes(enum_name, class_names):
    """Returns the enum value -> Inventor class mapping for the given enum"""
    if enum_name not in _type_classes:
        enum = getattr(InventorInterop, enum_name)
        _type_classes[enum_name] = {
            getattr(enum, member): getattr(InventorInterop, class_name)
            for member, class_name in class_names.items()
        }
    return _type_classes[enum_name]


def _cast_geometry(entity, geometry_type, type_classes):
    """
    Cast ``entity.Geometry`` using the class mapped to ``geometry_type``.
    Unmapped types return the uncast geometry, or ``None`` when Inventor
    cannot provide it.
    """
    geometry_class = type_classes.get(geometry_type)
    if geometry_class is None:
        # Inventor raises E_FAIL on Geometry for most unknown curve/surface types
        try:
            geometry = entity.Geometry
        except Exception as e:
            logger.debug(f"Geometry not available for type {geometry_type}: {getattr(e, 'Message', e)}")
            return None
        logger.warning(f"No geometry class for type {geometry_type}; returning uncast geometry")
        return geometry

    return geometry_class(entity.Geometry)


def get_edge_curve_type(edge):
    """
    Returns the curve type of an edge.

    :param edge: Edge object (raw COM object or InventorInterop.Edge)
    :return: InventorInterop.CurveTypeEnum value, e.g. kLineSegmentCurve
    """
    if not edge:
        raise ValueError("Edge not provided")

    return InventorInterop.Edge(edge).GeometryType


def cast_edge_geometry(edge):
    """
    Returns the curve type of an edge and its geometry cast to the
    matching Inventor class.

    :param edge: Edge object (raw COM object or InventorInterop.Edge)
    :return: tuple ``(curve_type, geometry)``. For ``kUnknownCurve`` the
             geometry is returned uncast, or ``None`` if Inventor cannot
             provide it (use ``edge.Evaluator`` for such edges).
    """
    if not edge:
        raise ValueError("Edge not provided")

    edge = InventorInterop.Edge(edge)
    curve_type = edge.GeometryType
    classes = _get_type_classes('CurveTypeEnum', _CURVE_TYPE_CLASS_NAMES)
    return curve_type, _cast_geometry(edge, curve_type, classes)


def get_face_surface_type(face):
    """
    Returns the surface type of a face.

    :param face: Face object (raw COM object or InventorInterop.Face)
    :return: InventorInterop.SurfaceTypeEnum value, e.g. kPlaneSurface
    """
    if not face:
        raise ValueError("Face not provided")

    return InventorInterop.Face(face).SurfaceType


def cast_face_geometry(face):
    """
    Returns the surface type of a face and its geometry cast to the
    matching Inventor class.

    :param face: Face object (raw COM object or InventorInterop.Face)
    :return: tuple ``(surface_type, geometry)``. For ``kUnknownSurface`` the
             geometry is returned uncast, or ``None`` if Inventor cannot
             provide it (use ``face.Evaluator`` for such faces).
    """
    if not face:
        raise ValueError("Face not provided")

    face = InventorInterop.Face(face)
    surface_type = face.SurfaceType
    classes = _get_type_classes('SurfaceTypeEnum', _SURFACE_TYPE_CLASS_NAMES)
    return surface_type, _cast_geometry(face, surface_type, classes)


# Extension methods: edge.cast_edge_geometry(), face.cast_face_geometry(), ...
# Assembly proxies (EdgeProxy, FaceProxy) are separate types, so they are registered too.
for _class_name in ('Edge', 'EdgeProxy'):
    register_extension(_class_name, 'get_edge_curve_type', get_edge_curve_type)
    register_extension(_class_name, 'cast_edge_geometry', cast_edge_geometry)

for _class_name in ('Face', 'FaceProxy'):
    register_extension(_class_name, 'get_face_surface_type', get_face_surface_type)
    register_extension(_class_name, 'cast_face_geometry', cast_face_geometry)
