"""Revolve feature builder for Onshape."""

from enum import Enum
from typing import Any, Dict, Optional


class RevolveType(Enum):
    """Revolve operation type."""

    NEW = "NEW"
    ADD = "ADD"
    REMOVE = "REMOVE"
    INTERSECT = "INTERSECT"


class RevolveBuilder:
    """Builder for creating Onshape revolve features."""

    def __init__(
        self,
        name: str = "Revolve",
        sketch_feature_id: Optional[str] = None,
        angle: float = 360.0,
        operation_type: RevolveType = RevolveType.NEW,
    ):
        """Initialize revolve builder.

        Args:
            name: Name of the revolve feature
            sketch_feature_id: ID of the sketch to revolve
            angle: Revolve angle in degrees
            operation_type: Type of revolve operation
        """
        self.name = name
        self.sketch_feature_id = sketch_feature_id
        self.axis_entity_id: Optional[str] = None
        self.angle = angle
        self.angle_variable: Optional[str] = None
        self.operation_type = operation_type
        self.opposite_direction = False

    def set_sketch(self, sketch_feature_id: str) -> "RevolveBuilder":
        """Set the sketch to revolve.

        Args:
            sketch_feature_id: Feature ID of the sketch

        Returns:
            Self for chaining
        """
        self.sketch_feature_id = sketch_feature_id
        return self

    def set_angle(self, angle: float, variable_name: Optional[str] = None) -> "RevolveBuilder":
        """Set revolve angle.

        Args:
            angle: Angle in degrees
            variable_name: Optional variable name to reference

        Returns:
            Self for chaining
        """
        self.angle = angle
        self.angle_variable = variable_name
        return self

    def set_axis_entity(self, entity_id: str) -> "RevolveBuilder":
        """Set the edge (or linear/cylindrical face) that defines the revolve axis.

        Onshape has no always-present "X/Y/Z axis" entity to select by default --
        the axis must be a real edge or face's deterministic ID. Use
        get_body_details or an eval_featurescript query (e.g. qCreatedBy(makeId(
        "<featureId>"), EntityType.EDGE) via evaluateQuery) to resolve one.

        Args:
            entity_id: Deterministic ID of the edge/face defining the axis

        Returns:
            Self for chaining
        """
        self.axis_entity_id = entity_id
        return self

    def set_opposite_direction(self, opposite: bool = True) -> "RevolveBuilder":
        """Set whether to revolve in opposite direction.

        Args:
            opposite: True to revolve in opposite direction

        Returns:
            Self for chaining
        """
        self.opposite_direction = opposite
        return self

    def _build_axis_query(self) -> Dict[str, Any]:
        """Build the axis query parameter.

        Returns:
            Axis query parameter dictionary
        """
        return {
            "btType": "BTMParameterQueryList-148",
            "queries": [
                {
                    "btType": "BTMIndividualQuery-138",
                    "deterministicIds": [self.axis_entity_id],
                }
            ],
            "parameterId": "axis",
        }

    def build(self) -> Dict[str, Any]:
        """Build the revolve feature JSON.

        Returns:
            Feature definition for Onshape API

        Raises:
            ValueError: If sketch feature ID or axis entity is not set
        """
        if not self.sketch_feature_id:
            raise ValueError("Sketch feature ID must be set before building revolve")
        if not self.axis_entity_id:
            raise ValueError(
                "Axis entity must be set via set_axis_entity() before building. "
                "Onshape has no default axis entity -- resolve a real edge/face ID first."
            )

        angle_expression = (
            f"#{self.angle_variable}" if self.angle_variable else f"{self.angle} deg"
        )

        return {
            "btType": "BTFeatureDefinitionCall-1406",
            "feature": {
                "btType": "BTMFeature-134",
                "featureType": "revolve",
                "name": self.name,
                "suppressed": False,
                "namespace": "",
                "parameters": [
                    {
                        "btType": "BTMParameterQueryList-148",
                        "queries": [
                            {
                                "btType": "BTMIndividualSketchRegionQuery-140",
                                "featureId": self.sketch_feature_id,
                            }
                        ],
                        "parameterId": "entities",
                    },
                    self._build_axis_query(),
                    {
                        "btType": "BTMParameterEnum-145",
                        "namespace": "",
                        "enumName": "NewBodyOperationType",
                        "value": self.operation_type.value,
                        "parameterId": "operationType",
                    },
                    {
                        "btType": "BTMParameterQuantity-147",
                        "isInteger": False,
                        "value": self.angle,
                        "units": "",
                        "expression": angle_expression,
                        "parameterId": "revolveAngle",
                    },
                    {
                        "btType": "BTMParameterBoolean-144",
                        "value": self.opposite_direction,
                        "parameterId": "oppositeDirection",
                    },
                ],
            },
        }
