#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Geneva mechanism example for PySharpInventor

    Creates a new part with an external Geneva drive as two solid bodies,
    placed in the locked position:

    - Drive wheel: base plate with a drive pin, and a crescent-shaped
      locking disc on top.
    - Geneva wheel: disc with radial slots and concave locking arcs.

    All lengths are in cm (Inventor API internal units).
"""

import math
from collections import Counter

from pysharpinventor import Inventor, InventorInterop


class GenevaDesign(object):
    """
    Geometry of an external Geneva drive, derived from the slot count,
    centre distance and pin size.

    :param slots: number of slots in the Geneva wheel (3 or more)
    :param center_distance: distance between the drive and Geneva wheel axes
    :param pin_radius: radius of the drive pin
    :param thickness: thickness of each layer (base plate, locking disc, Geneva wheel)
    :param clearance: running clearance between moving surfaces
    :param bore_radius: radius of the shaft bore in each wheel
    """

    def __init__(self, slots=4, center_distance=10.0, pin_radius=0.5,
                 thickness=1.0, clearance=0.05, bore_radius=0.5):
        if slots < 3:
            raise ValueError("A Geneva wheel needs at least 3 slots")

        self.slots = slots
        self.center_distance = center_distance
        self.pin_radius = pin_radius
        self.thickness = thickness
        self.clearance = clearance
        self.bore_radius = bore_radius

        half_pitch = math.pi / slots
        # The pin enters each slot tangentially, so the pin circle, the Geneva
        # radius and the centre distance form a right angle at the pin.
        self.crank_radius = center_distance * math.sin(half_pitch)
        self.geneva_radius = center_distance * math.cos(half_pitch)
        # Closest approach of the pin centre to the Geneva centre; the rounded
        # slot end is centred here so the slot is exactly as deep as needed
        self.slot_end_radius = center_distance - self.crank_radius
        self.slot_half_width = pin_radius + clearance
        self.locking_radius = self.crank_radius - 1.5 * pin_radius
        self.base_radius = self.crank_radius + 2 * pin_radius

        self._check()

    def _check(self):
        """Reject parameter combinations that produce overlapping cuts"""
        # Each concave locking arc must stay clear of the neighbouring slots
        arc_to_slot = self.center_distance * math.sin(math.pi / self.slots)
        if arc_to_slot <= self.locking_radius + self.slot_half_width:
            raise ValueError("Locking arcs overlap the slots; increase center_distance "
                             "or reduce pin_radius")
        # The locking arcs must actually cut into the Geneva wheel
        if self.center_distance - self.locking_radius >= self.geneva_radius:
            raise ValueError("Locking arcs miss the Geneva wheel; reduce pin_radius")

    @property
    def drive_angle(self):
        """Drive rotation (degrees) during which the Geneva wheel moves"""
        return 180.0 - 360.0 / self.slots

    @property
    def dwell_angle(self):
        """Drive rotation (degrees) during which the Geneva wheel is locked"""
        return 360.0 - self.drive_angle


def _new_body_collection(app, body):
    """ObjectCollection holding one body, for ExtrudeDefinition.AffectedBodies"""
    collection = app.TransientObjects.CreateObjectCollection()
    collection.Add(body)
    return collection


def _extrude(comp_def, profile, operation, distance, affected_body=None, app=None):
    """Extrude a profile by a distance in the sketch normal direction"""
    extrudes = comp_def.Features.ExtrudeFeatures
    extrude_def = extrudes.CreateExtrudeDefinition(profile, operation)
    extrude_def.SetDistanceExtent(
        distance, InventorInterop.PartFeatureExtentDirectionEnum.kPositiveExtentDirection
    )
    if affected_body is not None:
        # In a multi-body part, restrict join/cut to one body
        extrude_def.AffectedBodies = _new_body_collection(app, affected_body)
    return extrudes.Add(extrude_def)


def _circle_intersection(r1, center2_x, r2):
    """
    Upper intersection point of a circle of radius r1 at the origin and a
    circle of radius r2 at (center2_x, 0).
    """
    x = (r1 ** 2 - r2 ** 2 + center2_x ** 2) / (2 * center2_x)
    return x, math.sqrt(r1 ** 2 - x ** 2)


def create_drive_wheel(app, comp_def, design, top_plane):
    """
    Drive wheel at the origin, pin pointing in -X (away from the Geneva wheel).

    :return: SurfaceBody of the drive wheel
    """
    tg = app.TransientGeometry
    d = design

    # Base plate on the XY plane (WorkPlanes: 1=YZ, 2=XZ, 3=XY)
    sketch = comp_def.Sketches.Add(comp_def.WorkPlanes[3])
    sketch.SketchCircles.AddByCenterRadius(tg.CreatePoint2d(0, 0), d.base_radius)
    feature = _extrude(comp_def, sketch.Profiles.AddForSolid(),
                       InventorInterop.PartFeatureOperationEnum.kNewBodyOperation,
                       d.thickness)
    body = feature.SurfaceBodies[1]
    body.Name = "Drive wheel"

    # Locking disc with a clearance cutout facing the pin, plus the pin itself
    sketch = comp_def.Sketches.Add(top_plane)
    cutout_center_x = -d.center_distance
    cutout_radius = d.geneva_radius + d.clearance
    lock_radius = d.locking_radius - d.clearance
    x, y = _circle_intersection(lock_radius, cutout_center_x, cutout_radius)

    # Convex arc around the +X side, then concave arc back along the cutout
    lock_arc = sketch.SketchArcs.AddByCenterStartEndPoint(
        tg.CreatePoint2d(0, 0), tg.CreatePoint2d(x, -y), tg.CreatePoint2d(x, y), True
    )
    sketch.SketchArcs.AddByCenterStartEndPoint(
        tg.CreatePoint2d(cutout_center_x, 0), lock_arc.StartSketchPoint,
        lock_arc.EndSketchPoint, True
    )
    sketch.SketchCircles.AddByCenterRadius(tg.CreatePoint2d(-d.crank_radius, 0), d.pin_radius)

    _extrude(comp_def, sketch.Profiles.AddForSolid(),
             InventorInterop.PartFeatureOperationEnum.kJoinOperation,
             d.thickness, affected_body=body, app=app)
    return body


def create_geneva_wheel(app, comp_def, design, top_plane):
    """
    Geneva wheel at (center_distance, 0), on the same level as the locking
    disc, rotated so a locking arc faces the drive wheel.

    :return: SurfaceBody of the Geneva wheel
    """
    tg = app.TransientGeometry
    d = design
    cx = d.center_distance

    # Wheel blank
    sketch = comp_def.Sketches.Add(top_plane)
    sketch.SketchCircles.AddByCenterRadius(tg.CreatePoint2d(cx, 0), d.geneva_radius)
    feature = _extrude(comp_def, sketch.Profiles.AddForSolid(),
                       InventorInterop.PartFeatureOperationEnum.kNewBodyOperation,
                       d.thickness)
    body = feature.SurfaceBodies[1]
    body.Name = "Geneva wheel"

    # Slots and locking arcs, cut in one feature
    sketch = comp_def.Sketches.Add(top_plane)
    pitch = 2 * math.pi / d.slots
    outer = d.geneva_radius + 1.0  # slots run out past the rim
    w = d.slot_half_width
    r0 = d.slot_end_radius  # centre of the rounded slot end

    def point(radius, along, angle):
        """Point at `radius` along `angle` from the wheel centre, offset `along` sideways"""
        return tg.CreatePoint2d(
            cx + radius * math.cos(angle) - along * math.sin(angle),
            radius * math.sin(angle) + along * math.cos(angle)
        )

    for i in range(d.slots):
        # Locking arc faces the drive (-X); slots sit half a pitch either side
        arc_angle = math.pi + i * pitch
        slot_angle = arc_angle + pitch / 2

        # Slot: side line, rounded end, side line, closing line outside the rim
        side_a = sketch.SketchLines.AddByTwoPoints(point(outer, w, slot_angle),
                                                   point(r0, w, slot_angle))
        end = sketch.SketchArcs.AddByCenterStartEndPoint(
            point(r0, 0, slot_angle), side_a.EndSketchPoint, point(r0, -w, slot_angle), True
        )
        side_b = sketch.SketchLines.AddByTwoPoints(end.EndSketchPoint,
                                                   point(outer, -w, slot_angle))
        sketch.SketchLines.AddByTwoPoints(side_b.EndSketchPoint, side_a.StartSketchPoint)

        # Concave locking arc, centred where the drive axis sits in the locked position
        sketch.SketchCircles.AddByCenterRadius(point(d.center_distance, 0, arc_angle),
                                               d.locking_radius)

    _extrude(comp_def, sketch.Profiles.AddForSolid(),
             InventorInterop.PartFeatureOperationEnum.kCutOperation,
             d.thickness, affected_body=body, app=app)
    return body


def cut_bores(app, comp_def, design, bodies):
    """Shaft bores through both wheels"""
    tg = app.TransientGeometry
    sketch = comp_def.Sketches.Add(comp_def.WorkPlanes[3])
    sketch.SketchCircles.AddByCenterRadius(tg.CreatePoint2d(0, 0), design.bore_radius)
    sketch.SketchCircles.AddByCenterRadius(tg.CreatePoint2d(design.center_distance, 0),
                                           design.bore_radius)

    extrudes = comp_def.Features.ExtrudeFeatures
    extrude_def = extrudes.CreateExtrudeDefinition(
        sketch.Profiles.AddForSolid(), InventorInterop.PartFeatureOperationEnum.kCutOperation
    )
    extrude_def.SetThroughAllExtent(
        InventorInterop.PartFeatureExtentDirectionEnum.kPositiveExtentDirection
    )
    collection = app.TransientObjects.CreateObjectCollection()
    for body in bodies:
        collection.Add(body)
    extrude_def.AffectedBodies = collection
    extrudes.Add(extrude_def)


def create_geneva_mechanism(inv, design=None):
    """
    Create a new part document containing a Geneva mechanism.

    :param inv: Inventor object
    :param design: GenevaDesign; defaults to a 4-slot, 10 cm centre distance drive
    :return: (PartDocument, drive wheel body, Geneva wheel body)
    """
    design = design or GenevaDesign()
    app = inv.app

    template = app.FileManager.GetTemplateFile(InventorInterop.DocumentTypeEnum.kPartDocumentObject)
    doc = app.Documents.Add(InventorInterop.DocumentTypeEnum.kPartDocumentObject, template, True)
    part_doc = InventorInterop.PartDocument(doc)
    comp_def = part_doc.ComponentDefinition

    # Locking disc and Geneva wheel sit on top of the drive's base plate
    top_plane = comp_def.WorkPlanes.AddByPlaneAndOffset(comp_def.WorkPlanes[3], design.thickness)
    top_plane.Visible = False

    drive = create_drive_wheel(app, comp_def, design, top_plane)
    geneva = create_geneva_wheel(app, comp_def, design, top_plane)
    cut_bores(app, comp_def, design, [drive, geneva])

    app.ActiveView.Fit()
    return part_doc, drive, geneva


if __name__ == "__main__":
    # Connect to active Inventor instance (start one if needed)
    inv = Inventor(create_if_not_exists=True)
    print(f"Inventor Application: {inv.app.Caption}")

    design = GenevaDesign(slots=4, center_distance=10.0, pin_radius=0.5)
    part_doc, drive, geneva = create_geneva_mechanism(inv, design)
    print(f"Created: {part_doc.DisplayName}")

    print(f"{design.slots} slots, centre distance {design.center_distance} cm")
    print(f"  crank radius {design.crank_radius:.3f} cm, Geneva radius {design.geneva_radius:.3f} cm")
    print(f"  Geneva moves during {design.drive_angle:.0f} deg of drive rotation, "
          f"dwells for {design.dwell_angle:.0f} deg")

    # Volume is a parameterised property in .NET, exposed as get_Volume(tolerance)
    # Summarise each body's faces using the geometry extension methods
    for body in (drive, geneva):
        types = Counter(str(InventorInterop.Face(face).cast_face_geometry()[0])
                        for face in body.Faces)
        print(f"{body.Name}: volume {body.get_Volume(0.001):.2f} cm^3, faces {dict(types)}")
