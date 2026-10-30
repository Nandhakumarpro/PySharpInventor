#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    pysharpinventor.selectors
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    CadQuery-style string selectors for faces, edges and vertices::

        top = body.select_faces(">Z")[0]
        holes = top.select_edges("%CIRCLE")
        vertical = body.select_edges("|Z and >X")

    Selector syntax:

    - ``>D`` / ``<D``: farthest / nearest along direction ``D``, measured
      at the entity centre. ``>D[n]`` / ``<D[n]`` select the n-th group
      (0-based, negative counts from the other end); entities at the same
      distance form one group.
    - ``|D``: parallel to ``D``; ``#D``: perpendicular to ``D``.
    - ``+D`` / ``-D``: pointing in / against direction ``D``.
    - ``%TYPE``: geometry type, e.g. ``%PLANE``, ``%CYLINDER``, ``%LINE``,
      ``%CIRCLE``.
    - ``and``, ``or``, ``not``, ``exc`` and parentheses; precedence is
      ``not`` > ``and`` > ``or`` > ``exc``.

    ``D`` is ``X``, ``Y``, ``Z`` or a vector such as ``(1, 1, 0)``.

    As in CadQuery, ``|``, ``#``, ``+`` and ``-`` only match planar faces
    (by outward normal) and straight edges (by direction).

    :copyright: (c) 2026
    :license: BSD, see LICENSE.txt for more details.
"""

import math
import re

from pysharpinventor._interop import InventorInterop, register_extension

__all__ = ['select_faces', 'select_edges', 'select_vertices']

# Distance tolerance (cm) for grouping entities along a direction
TOLERANCE = 1e-4
# Tolerance on the dot product of unit vectors for direction tests
ANGLE_TOLERANCE = 1e-6

_AXES = {'X': (1.0, 0.0, 0.0), 'Y': (0.0, 1.0, 0.0), 'Z': (0.0, 0.0, 1.0)}

# Selector type name -> SurfaceTypeEnum member names
_FACE_TYPE_NAMES = {
    'PLANE': ('kPlaneSurface',),
    'CYLINDER': ('kCylinderSurface', 'kEllipticalCylinderSurface'),
    'CONE': ('kConeSurface', 'kEllipticalConeSurface'),
    'SPHERE': ('kSphereSurface',),
    'TORUS': ('kTorusSurface',),
    'BSPLINE': ('kBSplineSurface',),
}

# Selector type name -> CurveTypeEnum member names
_EDGE_TYPE_NAMES = {
    'LINE': ('kLineCurve', 'kLineSegmentCurve'),
    'CIRCLE': ('kCircleCurve', 'kCircularArcCurve'),
    'ELLIPSE': ('kEllipseFullCurve', 'kEllipticalArcCurve'),
    'BSPLINE': ('kBSplineCurve',),
    'POLYLINE': ('kPolylineCurve',),
}

# Enum name -> {enum value: selector type name}, built on first use (needs the Interop DLL)
_type_names = {}


def _get_type_names(enum_name, names):
    if enum_name not in _type_names:
        enum = getattr(InventorInterop, enum_name)
        _type_names[enum_name] = {
            getattr(enum, member): name
            for name, members in names.items() for member in members
        }
    return _type_names[enum_name]


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _normalize(v):
    length = math.sqrt(_dot(v, v))
    if length == 0:
        raise ValueError("Selector direction cannot be a zero vector")
    return tuple(c / length for c in v)


def _box_center(box):
    lo, hi = box.MinPoint, box.MaxPoint
    return ((lo.X + hi.X) / 2, (lo.Y + hi.Y) / 2, (lo.Z + hi.Z) / 2)


class _Item(object):
    """A face, edge or vertex with its centre, direction and type computed on demand"""

    def __init__(self, entity, kind):
        self.entity = entity
        self.kind = kind
        self._center = None
        self._direction = False  # None is a valid direction (non-planar / non-linear)
        self._type_name = False

    @property
    def center(self):
        """Bounding-box centre; the point itself for a vertex"""
        if self._center is None:
            if self.kind == 'Vertex':
                p = self.entity.Point
                self._center = (p.X, p.Y, p.Z)
            else:
                self._center = _box_center(self.entity.Evaluator.RangeBox)
        return self._center

    @property
    def type_name(self):
        if self._type_name is False:
            if self.kind == 'Face':
                names = _get_type_names('SurfaceTypeEnum', _FACE_TYPE_NAMES)
                self._type_name = names.get(self.entity.SurfaceType)
            elif self.kind == 'Edge':
                names = _get_type_names('CurveTypeEnum', _EDGE_TYPE_NAMES)
                self._type_name = names.get(self.entity.GeometryType)
            else:
                self._type_name = None
        return self._type_name

    @property
    def direction(self):
        """Outward normal of a planar face, direction of a straight edge, else None"""
        if self._direction is False:
            self._direction = None
            if self.kind == 'Face' and self.type_name == 'PLANE':
                n = InventorInterop.Plane(self.entity.Geometry).Normal
                sign = -1.0 if self.entity.IsParamReversed else 1.0
                self._direction = (sign * n.X, sign * n.Y, sign * n.Z)
            elif self.kind == 'Edge' and self.type_name == 'LINE':
                geometry = self.entity.Geometry
                if self.entity.GeometryType == InventorInterop.CurveTypeEnum.kLineCurve:
                    d = InventorInterop.Line(geometry).Direction
                else:
                    d = InventorInterop.LineSegment(geometry).Direction
                self._direction = (d.X, d.Y, d.Z)
        return self._direction


# Selectors: each filter() takes a list of _Item and returns the matching ones in order

class _TypeSelector(object):
    def __init__(self, type_name):
        self.type_name = type_name

    def filter(self, items):
        return [item for item in items if item.type_name == self.type_name]


class _DirectionSelector(object):
    """``|D``, ``#D``, ``+D`` and ``-D``"""

    def __init__(self, op, direction):
        self.op = op
        self.direction = direction

    def test(self, d):
        dot = _dot(d, self.direction)
        if self.op == '|':
            return abs(dot) >= 1 - ANGLE_TOLERANCE
        if self.op == '#':
            return abs(dot) <= ANGLE_TOLERANCE
        if self.op == '+':
            return dot >= 1 - ANGLE_TOLERANCE
        return dot <= -1 + ANGLE_TOLERANCE

    def filter(self, items):
        return [item for item in items
                if item.direction is not None and self.test(item.direction)]


class _DirectionNthSelector(object):
    """``>D[n]`` and ``<D[n]``; ``>D`` is ``>D[0]``"""

    def __init__(self, direction, maximum, index=0):
        self.direction = direction
        self.maximum = maximum
        self.index = index

    def filter(self, items):
        ranked = sorted(items, key=lambda item: _dot(item.center, self.direction),
                        reverse=self.maximum)
        groups = []
        last = None
        for item in ranked:
            distance = _dot(item.center, self.direction)
            if groups and abs(distance - last) <= TOLERANCE:
                groups[-1].append(item)
            else:
                groups.append([item])
            last = distance
        try:
            selected = groups[self.index]
        except IndexError:
            return []
        # Keep the original order of the input
        return [item for item in items if item in selected]


class _Not(object):
    def __init__(self, operand):
        self.operand = operand

    def filter(self, items):
        excluded = self.operand.filter(items)
        return [item for item in items if item not in excluded]


class _Binary(object):
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

    def filter(self, items):
        left = self.left.filter(items)
        right = self.right.filter(items)
        if self.op == 'and':
            return [item for item in left if item in right]
        if self.op == 'or':
            return [item for item in items if item in left or item in right]
        return [item for item in left if item not in right]  # exc


# Parser

_TOKEN = re.compile(r"""
    \s*(?:
        (?P<dir>[<>|\#+-])\s*(?P<axis>[XYZxyz]\b|\([^)]*\))
            (?:\s*\[\s*(?P<index>-?\d+)\s*\])?
      | %(?P<type>[A-Za-z]+)
      | (?P<op>and|or|not|exc)\b
      | (?P<paren>[()])
    )""", re.VERBOSE)


def _parse_direction(text):
    if text.upper() in _AXES:
        return _AXES[text.upper()]
    try:
        values = tuple(float(v) for v in text.strip('()').split(','))
    except ValueError:
        values = ()
    if len(values) != 3:
        raise ValueError(f"Invalid selector direction: {text}")
    return _normalize(values)


def _tokenize(selector):
    tokens = []
    pos = 0
    selector = selector.rstrip()
    while pos < len(selector):
        match = _TOKEN.match(selector, pos)
        if not match:
            raise ValueError(f"Invalid selector {selector!r} at position {pos}: "
                             f"{selector[pos:].strip()!r}")
        pos = match.end()
        if match.group('dir'):
            op = match.group('dir')
            direction = _parse_direction(match.group('axis'))
            index = match.group('index')
            if op in '<>':
                tokens.append(_DirectionNthSelector(direction, op == '>', int(index or 0)))
            elif index is not None:
                raise ValueError(f"Index is only allowed after '>' or '<': {match.group().strip()!r}")
            else:
                tokens.append(_DirectionSelector(op, direction))
        elif match.group('type'):
            tokens.append(_TypeSelector(match.group('type').upper()))
        else:
            tokens.append(match.group('op') or match.group('paren'))
            continue
        tokens[-1].text = match.group().strip()  # for error messages
    return tokens


class _Parser(object):
    """Recursive descent parser: exc < or < and < not < atom"""

    _LEVELS = ('exc', 'or', 'and')

    def __init__(self, selector):
        self.selector = selector
        self.tokens = _tokenize(selector)
        self.pos = 0

    def parse(self):
        if not self.tokens:
            raise ValueError("Empty selector")
        result = self._binary(0)
        if self.pos != len(self.tokens):
            raise ValueError(f"Invalid selector {self.selector!r}: unexpected {getattr(self.tokens[self.pos], 'text', self.tokens[self.pos])!r}")
        return result

    def _peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _binary(self, level):
        if level == len(self._LEVELS):
            return self._unary()
        op = self._LEVELS[level]
        left = self._binary(level + 1)
        while self._peek() == op:
            self.pos += 1
            left = _Binary(op, left, self._binary(level + 1))
        return left

    def _unary(self):
        token = self._peek()
        if token == 'not':
            self.pos += 1
            return _Not(self._unary())
        if token == '(':
            self.pos += 1
            result = self._binary(0)
            if self._peek() != ')':
                raise ValueError(f"Invalid selector {self.selector!r}: missing ')'")
            self.pos += 1
            return result
        if token is None or isinstance(token, str):
            raise ValueError(f"Invalid selector {self.selector!r}: expected a selector, got {token!r}")
        self.pos += 1
        return token


def _check_types(node, kind):
    """Reject %TYPE names that can never match this kind of entity"""
    if isinstance(node, _TypeSelector):
        valid = {'Face': _FACE_TYPE_NAMES, 'Edge': _EDGE_TYPE_NAMES}.get(kind, {})
        if node.type_name not in valid:
            raise ValueError(f"Unknown {kind.lower()} type %{node.type_name}; "
                             f"expected one of {', '.join(sorted(valid)) or 'none'}")
    for child in ('operand', 'left', 'right'):
        if hasattr(node, child):
            _check_types(getattr(node, child), kind)


def _select(source, selector, kind):
    """
    Select entities of ``kind`` ('Face', 'Edge' or 'Vertex') from ``source``:
    an object with a ``Faces`` / ``Edges`` / ``Vertices`` collection (body,
    face, edge, ...) or an iterable of entities.
    """
    if source is None:
        raise ValueError("Selection source not provided")
    if not isinstance(selector, str):
        raise TypeError("Selector must be a string")

    root = _Parser(selector).parse()
    _check_types(root, kind)

    collection_name = 'Vertices' if kind == 'Vertex' else kind + 's'
    entities = getattr(source, collection_name, source)
    # Iterating a collection yields untyped COM objects; cast them
    entity_class = getattr(InventorInterop, kind)
    items = [_Item(entity_class(entity), kind) for entity in entities]
    return [item.entity for item in root.filter(items)]


def select_faces(source, selector):
    """
    Select faces with a CadQuery-style string selector.

    :param source: SurfaceBody, Edge, ... (anything with ``Faces``) or an iterable of faces
    :param selector: selector string, e.g. ``">Z"``, ``"%CYLINDER"``, ``"|Z and not >Z"``
    :return: list of InventorInterop.Face, in collection order
    """
    return _select(source, selector, 'Face')


def select_edges(source, selector):
    """
    Select edges with a CadQuery-style string selector.

    :param source: SurfaceBody, Face, ... (anything with ``Edges``) or an iterable of edges
    :param selector: selector string, e.g. ``"|Z"``, ``"%CIRCLE"``, ``">X[1]"``
    :return: list of InventorInterop.Edge, in collection order
    """
    return _select(source, selector, 'Edge')


def select_vertices(source, selector):
    """
    Select vertices with a CadQuery-style string selector. Only ``>``/``<``
    selectors apply to vertices.

    :param source: SurfaceBody, Face, Edge, ... (anything with ``Vertices``) or an iterable of vertices
    :param selector: selector string, e.g. ``">X and >Y and >Z"``
    :return: list of InventorInterop.Vertex, in collection order
    """
    return _select(source, selector, 'Vertex')


# Extension methods: body.select_faces(">Z"), face.select_edges("%CIRCLE"), ...
for _class_name in ('SurfaceBody', 'SurfaceBodyProxy'):
    register_extension(_class_name, 'select_faces', select_faces)
    register_extension(_class_name, 'select_edges', select_edges)
    register_extension(_class_name, 'select_vertices', select_vertices)

for _class_name in ('Face', 'FaceProxy'):
    register_extension(_class_name, 'select_edges', select_edges)
    register_extension(_class_name, 'select_vertices', select_vertices)

for _class_name in ('Edge', 'EdgeProxy'):
    register_extension(_class_name, 'select_faces', select_faces)
    register_extension(_class_name, 'select_vertices', select_vertices)
