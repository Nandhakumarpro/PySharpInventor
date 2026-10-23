#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Hello World example for PySharpInventor

    Creates a new part with a cube and prints its faces.
"""

from pysharpinventor import Inventor, InventorInterop
from pysharpinventor.geometry import cast_face_geometry


def create_cube(inv, size=5.0):
    """
    Create a new part document containing a cube.

    :param inv: Inventor object
    :param size: cube edge length in cm (Inventor API internal units)
    :return: PartDocument
    """
    app = inv.app
    tg = app.TransientGeometry

    # New part document from the default template
    template = app.FileManager.GetTemplateFile(InventorInterop.DocumentTypeEnum.kPartDocumentObject)
    doc = app.Documents.Add(InventorInterop.DocumentTypeEnum.kPartDocumentObject, template, True)
    part_doc = InventorInterop.PartDocument(doc)
    comp_def = part_doc.ComponentDefinition

    # Square sketch on the XY plane (WorkPlanes: 1=YZ, 2=XZ, 3=XY)
    sketch = comp_def.Sketches.Add(comp_def.WorkPlanes[3])
    sketch.SketchLines.AddAsTwoPointRectangle(
        tg.CreatePoint2d(0, 0),
        tg.CreatePoint2d(size, size)
    )
    profile = sketch.Profiles.AddForSolid()

    # Extrude the square by the same size to make a cube
    extrude_def = comp_def.Features.ExtrudeFeatures.CreateExtrudeDefinition(
        profile, InventorInterop.PartFeatureOperationEnum.kJoinOperation
    )
    extrude_def.SetDistanceExtent(
        size, InventorInterop.PartFeatureExtentDirectionEnum.kPositiveExtentDirection
    )
    comp_def.Features.ExtrudeFeatures.Add(extrude_def)

    app.ActiveView.Fit()
    return part_doc


if __name__ == "__main__":
    # Connect to active Inventor instance (start one if needed)
    inv = Inventor(create_if_not_exists=True)
    print(f"Inventor Application: {inv.app.Caption}")

    part_doc = create_cube(inv, size=5.0)
    print(f"Created: {part_doc.DisplayName}")

    # Inspect the cube's faces using the geometry helpers
    body = part_doc.ComponentDefinition.SurfaceBodies[1]
    for i, face in enumerate(body.Faces, start=1):
        face = InventorInterop.Face(face)
        surface_type, plane = cast_face_geometry(face)
        # Plane.Normal can point into the solid; flip it to get the outward normal
        n = plane.Normal
        sign = -1 if face.IsParamReversed else 1
        normal = tuple(round(sign * c) for c in (n.X, n.Y, n.Z))
        print(f"Face {i}: {surface_type}, area={face.Evaluator.Area:.2f} cm^2, "
              f"outward normal={normal}")
