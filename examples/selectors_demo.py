#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    String selectors example for PySharpInventor

    Creates a stepped block with a through hole, then uses CadQuery-style
    selectors to pick faces, edges and vertices, and to place a fillet,
    a chamfer and a sketch.

    All lengths are in cm (Inventor API internal units).
"""

from pysharpinventor import Inventor, InventorInterop
from pysharpinventor.selectors import select_faces


def _extrude(comp_def, sketch, operation, distance,
             direction=InventorInterop.PartFeatureExtentDirectionEnum.kPositiveExtentDirection):
    """Extrude the sketch's profile by a distance"""
    extrudes = comp_def.Features.ExtrudeFeatures
    extrude_def = extrudes.CreateExtrudeDefinition(sketch.Profiles.AddForSolid(), operation)
    extrude_def.SetDistanceExtent(distance, direction)
    return extrudes.Add(extrude_def)


def create_stepped_block(inv):
    """
    Create a new part with a 10 x 6 x 4 block, a 2 cm step cut from the +X
    end, and a through hole of radius 1.

    :return: (PartDocument, component definition)
    """
    app = inv.app
    template = app.FileManager.GetTemplateFile(InventorInterop.DocumentTypeEnum.kPartDocumentObject)
    doc = app.Documents.Add(InventorInterop.DocumentTypeEnum.kPartDocumentObject, template, True)
    part_doc = InventorInterop.PartDocument(doc)
    comp_def = part_doc.ComponentDefinition
    tg = app.TransientGeometry
    ops = InventorInterop.PartFeatureOperationEnum
    down = InventorInterop.PartFeatureExtentDirectionEnum.kNegativeExtentDirection

    # Block on the XY plane (WorkPlanes: 1=YZ, 2=XZ, 3=XY)
    sketch = comp_def.Sketches.Add(comp_def.WorkPlanes[3])
    sketch.SketchLines.AddAsTwoPointRectangle(tg.CreatePoint2d(0, 0), tg.CreatePoint2d(10, 6))
    _extrude(comp_def, sketch, ops.kNewBodyOperation, 4)

    top_plane = comp_def.WorkPlanes.AddByPlaneAndOffset(comp_def.WorkPlanes[3], 4)
    top_plane.Visible = False

    # Step: remove x > 6 down to z = 2
    sketch = comp_def.Sketches.Add(top_plane)
    sketch.SketchLines.AddAsTwoPointRectangle(tg.CreatePoint2d(6, -1), tg.CreatePoint2d(11, 7))
    _extrude(comp_def, sketch, ops.kCutOperation, 2, down)

    # Through hole
    sketch = comp_def.Sketches.Add(top_plane)
    sketch.SketchCircles.AddByCenterRadius(tg.CreatePoint2d(3, 3), 1)
    _extrude(comp_def, sketch, ops.kCutOperation, 5, down)

    app.ActiveView.Fit()
    return part_doc, comp_def


def _center(entity):
    """Bounding-box centre of a face or edge, rounded for printing"""
    box = entity.Evaluator.RangeBox
    lo, hi = box.MinPoint, box.MaxPoint
    return tuple(round((a + b) / 2, 2) for a, b in ((lo.X, hi.X), (lo.Y, hi.Y), (lo.Z, hi.Z)))


def show_selections(body):
    """Print what a few selectors pick on the body"""
    face_selectors = [
        (">Z", "highest face"),
        (">Z[1]", "second-highest group (by centre)"),
        ("|Z", "horizontal faces"),
        ("+Z", "upward faces"),
        ("#Z", "vertical planar faces"),
        ("%CYLINDER", "cylindrical faces"),
        ("+X exc >X", "+X faces except the end face"),
    ]
    print("Faces:")
    for selector, meaning in face_selectors:
        faces = body.select_faces(selector)
        print(f"  {selector:12s} {meaning:34s} {len(faces)} at {[_center(f) for f in faces]}")

    edge_selectors = [
        ("|Z", "vertical straight edges"),
        ("|Z and >X", "vertical edges at max X"),
        ("%CIRCLE", "circular edges"),
        ("%CIRCLE and >Z", "top rim of the hole"),
    ]
    print("Edges:")
    for selector, meaning in edge_selectors:
        edges = body.select_edges(selector)
        print(f"  {selector:16s} {meaning:30s} {len(edges)}")

    corner = body.select_vertices(">(1, 1, 1)")[0].Point
    print(f"Vertex farthest along (1, 1, 1): ({corner.X}, {corner.Y}, {corner.Z})")

    # Select from a face, and refine an earlier selection
    top = body.select_faces(">Z")[0]
    print(f"Top face: {len(top.select_edges('%LINE'))} straight edges, "
          f"{len(top.select_edges('%CIRCLE'))} circular edge")
    walls = select_faces(body.select_faces("%PLANE"), "#Z and not (>X or <X)")
    print(f"Planar walls other than the X ends: {len(walls)}")


def add_features(app, comp_def):
    """Fillet, chamfer and sketch placed using selectors"""
    features = comp_def.Features

    # Faces and edges change after each feature, so re-read the body every time
    body = comp_def.SurfaceBodies[1]
    edges = app.TransientObjects.CreateEdgeCollection()
    for edge in body.select_edges("|Z and >X"):
        edges.Add(edge)
    features.FilletFeatures.AddSimple(edges, 0.5)

    body = comp_def.SurfaceBodies[1]
    edges = app.TransientObjects.CreateEdgeCollection()
    for edge in body.select_edges("%CIRCLE and >Z"):
        edges.Add(edge)
    features.ChamferFeatures.AddUsingDistance(edges, 0.2)

    body = comp_def.SurfaceBodies[1]
    step = body.select_faces("+Z exc >Z")[0]
    sketch = comp_def.Sketches.Add(step)
    # Circle at the centre of the step face, converted from model to sketch space
    center = app.TransientGeometry.CreatePoint(*_center(step))
    sketch.SketchCircles.AddByCenterRadius(sketch.ModelToSketchSpace(center), 0.4)
    return sketch


if __name__ == "__main__":
    # Connect to active Inventor instance (start one if needed)
    inv = Inventor(create_if_not_exists=True)
    print(f"Inventor Application: {inv.app.Caption}")

    part_doc, comp_def = create_stepped_block(inv)
    print(f"Created: {part_doc.DisplayName}")

    show_selections(comp_def.SurfaceBodies[1])

    sketch = add_features(inv.app, comp_def)
    body = comp_def.SurfaceBodies[1]
    print(f"After fillet and chamfer: {body.Faces.Count} faces; "
          f"{sketch.Name} placed on the step face")
