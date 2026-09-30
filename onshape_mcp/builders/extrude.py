"""Extrude feature builder for Onshape."""

from typing import Any, Dict, Optional
from enum import Enum

from ..units import length_expression


class ExtrudeType(Enum):
    """Extrude operation type."""

    NEW = "NEW"
    ADD = "ADD"
    REMOVE = "REMOVE"
    INTERSECT = "INTERSECT"


class ExtrudeBuilder:
    """Builder for creating Onshape extrude features."""

    def __init__(
        self,
        name: str = "Extrude",
        sketch_feature_id: Optional[str] = None,
        depth: float = 1.0,
        operation_type: ExtrudeType = ExtrudeType.NEW,
        opposite_direction: bool = False,
    ):
        """Initialize extrude builder.

        Args:
            name: Name of the extrude feature
            sketch_feature_id: ID of the sketch to extrude
            depth: Extrude depth in the configured length unit
            operation_type: Type of extrude operation
            opposite_direction: Extrude away from the sketch plane's default
                normal direction instead of along it
        """
        self.name = name
        self.sketch_feature_id = sketch_feature_id
        self.depth = depth
        self.operation_type = operation_type
        self.opposite_direction = opposite_direction
        self.depth_variable: Optional[str] = None

    def set_depth(self, depth: float, variable_name: Optional[str] = None) -> "ExtrudeBuilder":
        """Set extrude depth.

        Args:
            depth: Depth in the configured length unit
            variable_name: Optional variable name to reference

        Returns:
            Self for chaining
        """
        self.depth = depth
        self.depth_variable = variable_name
        return self

    def set_opposite_direction(self, opposite: bool = True) -> "ExtrudeBuilder":
        """Set whether to extrude in the opposite direction.

        Args:
            opposite: True to extrude opposite the sketch plane's default normal

        Returns:
            Self for method chaining
        """
        self.opposite_direction = opposite
        return self

    def set_sketch(self, sketch_feature_id: str) -> "ExtrudeBuilder":
        """Set the sketch to extrude.

        Args:
            sketch_feature_id: Feature ID of the sketch

        Returns:
            Self for chaining
        """
        self.sketch_feature_id = sketch_feature_id
        return self

    def build(self) -> Dict[str, Any]:
        """Build the extrude feature JSON.

        Returns:
            Feature definition for Onshape API
        """
        if not self.sketch_feature_id:
            raise ValueError("Sketch feature ID must be set before building extrude")

        depth_expression = (
            f"#{self.depth_variable}" if self.depth_variable else length_expression(self.depth)
        )

        return {
            "btType": "BTFeatureDefinitionCall-1406",
            "feature": {
                "btType": "BTMFeature-134",
                "featureType": "extrude",
                "name": self.name,
                "suppressed": False,
                "namespace": "",
                "parameters": [
                    {
                        "btType": "BTMParameterQueryList-148",
                        "queries": [
                            {
                                "btType": "BTMIndividualSketchRegionQuery-140",
                                "queryStatement": None,
                                "filterInnerLoops": True,
                                "queryString": f'query = qSketchRegion(id + "{self.sketch_feature_id}", true);',
                                "featureId": self.sketch_feature_id,
                                "deterministicIds": [],
                            }
                        ],
                        "parameterId": "entities",
                        "parameterName": "",
                    },
                    {
                        "btType": "BTMParameterEnum-145",
                        "namespace": "",
                        "enumName": "NewBodyOperationType",
                        "value": self.operation_type.value,
                        "parameterId": "operationType",
                        "parameterName": "",
                    },
                    {
                        "btType": "BTMParameterQuantity-147",
                        "isInteger": False,
                        "value": self.depth,
                        "units": "",
                        "expression": depth_expression,
                        "parameterId": "depth",
                        "parameterName": "",
                    },
                    {
                        "btType": "BTMParameterBoolean-144",
                        "value": self.opposite_direction,
                        "parameterId": "oppositeDirection",
                        "parameterName": "",
                    },
                ],
            },
        }
