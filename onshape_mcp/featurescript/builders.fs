// MCP Builder Library — batch geometry creation features
// Each feature combines sketch + extrude (+ optional extras) into a single operation,
// reducing API calls from 2-8 per part down to 1.

FeatureScript 2892;
import(path : "onshape/std/geometry.fs", version : "2892.0");

// ============================================================================
// rectExtrude — Rectangle sketch + extrude in one feature
// Creates a rectangular solid on any standard plane.
// Supports NEW/ADD/REMOVE operations and optional draft angle.
// ============================================================================
annotation { "Feature Type Name" : "Rect Extrude",
             "Feature Name Template" : "Rect Extrude #name" }
export const rectExtrude = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Name" }
        definition.name is string;

        annotation { "Name" : "Plane", "UIHint" : UIHint.SHOW_LABEL }
        definition.sketchPlane is string; // "Front", "Top", "Right"

        annotation { "Name" : "Corner 1 X" }
        isLength(definition.x1, ZERO_DEFAULT_LENGTH_BOUNDS);

        annotation { "Name" : "Corner 1 Y" }
        isLength(definition.y1, ZERO_DEFAULT_LENGTH_BOUNDS);

        annotation { "Name" : "Corner 2 X" }
        isLength(definition.x2, ZERO_DEFAULT_LENGTH_BOUNDS);

        annotation { "Name" : "Corner 2 Y" }
        isLength(definition.y2, ZERO_DEFAULT_LENGTH_BOUNDS);

        annotation { "Name" : "Depth" }
        isLength(definition.depth, LENGTH_BOUNDS);

        annotation { "Name" : "Operation Type", "UIHint" : UIHint.SHOW_LABEL }
        definition.operationType is NewBodyOperationType;

        annotation { "Name" : "Has Draft" }
        definition.hasDraft is boolean;

        if (definition.hasDraft)
        {
            annotation { "Name" : "Draft Angle" }
            isAngle(definition.draftAngle, ANGLE_STRICT_90_BOUNDS);

            annotation { "Name" : "Draft Pull Direction" }
            definition.draftPullDirection is boolean;
        }
    }
    {
        // Resolve plane query
        var planeQuery = getPlaneQuery(definition.sketchPlane);

        // Create sketch
        var sketch = newSketch(context, id + "sketch", {
                "sketchPlane" : planeQuery
        });

        skRectangle(sketch, "rect", {
                "firstCorner" : vector(definition.x1, definition.y1),
                "secondCorner" : vector(definition.x2, definition.y2)
        });

        skSolve(sketch);

        // Extrude
        var extrudeDef = {
            "entities" : qSketchRegion(id + "sketch"),
            "direction" : evOwnerSketchPlane(context, { "entity" : qSketchRegion(id + "sketch") }).normal,
            "endBound" : BoundingType.BLIND,
            "endDepth" : definition.depth
        };

        if (definition.hasDraft)
        {
            extrudeDef.hasDraft = true;
            extrudeDef.draftAngle = definition.draftAngle;
            extrudeDef.draftPullDirection = definition.draftPullDirection;
        }

        opExtrude(context, id + "extrude", extrudeDef);

        // Handle operation type (boolean)
        if (definition.operationType != NewBodyOperationType.NEW)
        {
            var targetBodies = qAllModifiableSolidBodies()->qSubtraction(qCreatedBy(id + "extrude", EntityType.BODY));
            var toolBodies = qCreatedBy(id + "extrude", EntityType.BODY);

            if (definition.operationType == NewBodyOperationType.ADD)
            {
                opBoolean(context, id + "boolean", {
                        "tools" : qUnion([targetBodies, toolBodies]),
                        "operationType" : BooleanOperationType.UNION
                });
            }
            else if (definition.operationType == NewBodyOperationType.REMOVE)
            {
                opBoolean(context, id + "boolean", {
                        "targets" : targetBodies,
                        "tools" : toolBodies,
                        "operationType" : BooleanOperationType.SUBTRACTION
                });
            }
        }
    });


// ============================================================================
// polyExtrude — Polygon sketch + extrude in one feature
// Creates a solid from a closed polygon (trapezoid, triangle, etc.)
// Up to 8 vertices supported.
// ============================================================================
annotation { "Feature Type Name" : "Poly Extrude",
             "Feature Name Template" : "Poly Extrude #name" }
export const polyExtrude = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Name" }
        definition.name is string;

        annotation { "Name" : "Plane" }
        definition.sketchPlane is string;

        annotation { "Name" : "Vertex Count" }
        isInteger(definition.vertexCount, { (unitless) : [3, 4, 8] } as IntegerBoundSpec);

        // Vertices (up to 8 pairs)
        annotation { "Name" : "V1 X" }
        isLength(definition.v1x, ZERO_DEFAULT_LENGTH_BOUNDS);
        annotation { "Name" : "V1 Y" }
        isLength(definition.v1y, ZERO_DEFAULT_LENGTH_BOUNDS);
        annotation { "Name" : "V2 X" }
        isLength(definition.v2x, ZERO_DEFAULT_LENGTH_BOUNDS);
        annotation { "Name" : "V2 Y" }
        isLength(definition.v2y, ZERO_DEFAULT_LENGTH_BOUNDS);
        annotation { "Name" : "V3 X" }
        isLength(definition.v3x, ZERO_DEFAULT_LENGTH_BOUNDS);
        annotation { "Name" : "V3 Y" }
        isLength(definition.v3y, ZERO_DEFAULT_LENGTH_BOUNDS);

        if (definition.vertexCount >= 4)
        {
            annotation { "Name" : "V4 X" }
            isLength(definition.v4x, ZERO_DEFAULT_LENGTH_BOUNDS);
            annotation { "Name" : "V4 Y" }
            isLength(definition.v4y, ZERO_DEFAULT_LENGTH_BOUNDS);
        }

        annotation { "Name" : "Depth" }
        isLength(definition.depth, LENGTH_BOUNDS);

        annotation { "Name" : "Operation Type" }
        definition.operationType is NewBodyOperationType;
    }
    {
        var planeQuery = getPlaneQuery(definition.sketchPlane);

        var sketch = newSketch(context, id + "sketch", {
                "sketchPlane" : planeQuery
        });

        // Build vertex list
        var vertices = [
            vector(definition.v1x, definition.v1y),
            vector(definition.v2x, definition.v2y),
            vector(definition.v3x, definition.v3y)
        ];

        if (definition.vertexCount >= 4)
            vertices = append(vertices, vector(definition.v4x, definition.v4y));

        // Draw line segments
        for (var i = 0; i < size(vertices); i += 1)
        {
            var next = (i + 1) % size(vertices);
            skLineSegment(sketch, "line" ~ i, {
                    "start" : vertices[i],
                    "end" : vertices[next]
            });
        }

        // Add coincident constraints to close the polygon
        for (var i = 0; i < size(vertices); i += 1)
        {
            var next = (i + 1) % size(vertices);
            skConstraint(sketch, "coincident" ~ i, {
                    "constraintType" : ConstraintType.COINCIDENT,
                    "localFirst" : sketchEntityQuery(id + "sketch", EntityType.VERTEX, "line" ~ i ~ ".end"),
                    "localSecond" : sketchEntityQuery(id + "sketch", EntityType.VERTEX, "line" ~ next ~ ".start")
            });
        }

        skSolve(sketch);

        // Extrude
        opExtrude(context, id + "extrude", {
                "entities" : qSketchRegion(id + "sketch"),
                "direction" : evOwnerSketchPlane(context, { "entity" : qSketchRegion(id + "sketch") }).normal,
                "endBound" : BoundingType.BLIND,
                "endDepth" : definition.depth
        });
    });


// ============================================================================
// cabinetBox — Complete cabinet in one feature
// Creates: outer shell, interior cavity, optional divider, optional shelf
// ============================================================================
annotation { "Feature Type Name" : "Cabinet Box",
             "Feature Name Template" : "Cabinet Box #name" }
export const cabinetBox = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Name" }
        definition.name is string;

        annotation { "Name" : "Width" }
        isLength(definition.width, LENGTH_BOUNDS);

        annotation { "Name" : "Height" }
        isLength(definition.height, LENGTH_BOUNDS);

        annotation { "Name" : "Depth" }
        isLength(definition.depth, LENGTH_BOUNDS);

        annotation { "Name" : "Panel Thickness" }
        isLength(definition.panelThickness, LENGTH_BOUNDS);

        annotation { "Name" : "Centered on X" }
        definition.centeredX is boolean;

        annotation { "Name" : "Has Divider" }
        definition.hasDivider is boolean;

        annotation { "Name" : "Has Shelf" }
        definition.hasShelf is boolean;

        if (definition.hasShelf)
        {
            annotation { "Name" : "Shelf Height" }
            isLength(definition.shelfHeight, LENGTH_BOUNDS);
        }
    }
    {
        var xStart = definition.centeredX ? -definition.width / 2 : 0 * inch;
        var xEnd = definition.centeredX ? definition.width / 2 : definition.width;

        // 1. Outer shell sketch + extrude
        var outerSketch = newSketch(context, id + "outerSketch", {
                "sketchPlane" : qCreatedBy(makeId("Front"), EntityType.FACE)
        });
        skRectangle(outerSketch, "outer", {
                "firstCorner" : vector(xStart, 0 * inch),
                "secondCorner" : vector(xEnd, definition.height)
        });
        skSolve(outerSketch);

        opExtrude(context, id + "outerExtrude", {
                "entities" : qSketchRegion(id + "outerSketch"),
                "direction" : evOwnerSketchPlane(context, { "entity" : qSketchRegion(id + "outerSketch") }).normal,
                "endBound" : BoundingType.BLIND,
                "endDepth" : definition.depth
        });

        // 2. Interior cavity (remove)
        var t = definition.panelThickness;
        var cavitySketch = newSketch(context, id + "cavitySketch", {
                "sketchPlane" : qCreatedBy(makeId("Front"), EntityType.FACE)
        });
        skRectangle(cavitySketch, "cavity", {
                "firstCorner" : vector(xStart + t, t),
                "secondCorner" : vector(xEnd - t, definition.height - t)
        });
        skSolve(cavitySketch);

        var cavityDepth = definition.depth - t; // open front
        opExtrude(context, id + "cavityExtrude", {
                "entities" : qSketchRegion(id + "cavitySketch"),
                "direction" : evOwnerSketchPlane(context, { "entity" : qSketchRegion(id + "cavitySketch") }).normal,
                "endBound" : BoundingType.BLIND,
                "endDepth" : cavityDepth
        });

        opBoolean(context, id + "cavityBoolean", {
                "targets" : qCreatedBy(id + "outerExtrude", EntityType.BODY),
                "tools" : qCreatedBy(id + "cavityExtrude", EntityType.BODY),
                "operationType" : BooleanOperationType.SUBTRACTION
        });

        // 3. Vertical divider (centered)
        if (definition.hasDivider)
        {
            var divSketch = newSketch(context, id + "divSketch", {
                    "sketchPlane" : qCreatedBy(makeId("Front"), EntityType.FACE)
            });
            skRectangle(divSketch, "divider", {
                    "firstCorner" : vector(-t / 2, t),
                    "secondCorner" : vector(t / 2, definition.height - t)
            });
            skSolve(divSketch);

            opExtrude(context, id + "divExtrude", {
                    "entities" : qSketchRegion(id + "divSketch"),
                    "direction" : evOwnerSketchPlane(context, { "entity" : qSketchRegion(id + "divSketch") }).normal,
                    "endBound" : BoundingType.BLIND,
                    "endDepth" : cavityDepth
            });

            opBoolean(context, id + "divBoolean", {
                    "tools" : qUnion([qCreatedBy(id + "outerExtrude", EntityType.BODY), qCreatedBy(id + "divExtrude", EntityType.BODY)]),
                    "operationType" : BooleanOperationType.UNION
            });
        }

        // 4. Horizontal shelf
        if (definition.hasShelf)
        {
            var shelfY = definition.hasShelf ? definition.shelfHeight : definition.height / 2;
            var shelfSketch = newSketch(context, id + "shelfSketch", {
                    "sketchPlane" : qCreatedBy(makeId("Front"), EntityType.FACE)
            });
            skRectangle(shelfSketch, "shelf", {
                    "firstCorner" : vector(xStart + t, shelfY),
                    "secondCorner" : vector(xEnd - t, shelfY + t)
            });
            skSolve(shelfSketch);

            opExtrude(context, id + "shelfExtrude", {
                    "entities" : qSketchRegion(id + "shelfSketch"),
                    "direction" : evOwnerSketchPlane(context, { "entity" : qSketchRegion(id + "shelfSketch") }).normal,
                    "endBound" : BoundingType.BLIND,
                    "endDepth" : cavityDepth
            });

            opBoolean(context, id + "shelfBoolean", {
                    "tools" : qUnion([qAllModifiableSolidBodies(), qCreatedBy(id + "shelfExtrude", EntityType.BODY)]),
                    "operationType" : BooleanOperationType.UNION
            });
        }
    });


// ============================================================================
// Helper: resolve plane name to query
// ============================================================================
function getPlaneQuery(planeName is string)
{
    if (planeName == "Front")
        return qCreatedBy(makeId("Front"), EntityType.FACE);
    if (planeName == "Top")
        return qCreatedBy(makeId("Top"), EntityType.FACE);
    if (planeName == "Right")
        return qCreatedBy(makeId("Right"), EntityType.FACE);
    // Default to Front
    return qCreatedBy(makeId("Front"), EntityType.FACE);
}
