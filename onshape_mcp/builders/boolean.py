"""Boolean operation builder for Onshape."""

from enum import Enum
from typing import Any, Dict, List


class BooleanType(Enum):
    """Boolean operation type.

    Values match Onshape's ``BooleanOperationType`` FS enum: UNION,
    SUBTRACTION, INTERSECTION (NOT the shorter SUBTRACT/INTERSECT names —
    those would silently fail).
    """

    UNION = "UNION"
    SUBTRACT = "SUBTRACTION"
    INTERSECT = "INTERSECTION"


class BooleanBuilder:
    """Builder for creating Onshape boolean features."""

    def __init__(
        self,
        name: str = "Boolean",
        boolean_type: BooleanType = BooleanType.UNION,
    ):
        """Initialize boolean builder.

        Args:
            name: Name of the boolean feature
            boolean_type: Type of boolean operation
        """
        self.name = name
        self.boolean_type = boolean_type
        self.tool_body_queries: List[str] = []
        self.target_body_queries: List[str] = []

    def add_tool_body(self, body_id: str) -> "BooleanBuilder":
        """Add a tool body by its deterministic ID.

        Tool bodies are the bodies being combined into/subtracted from/
        intersected with the target.

        Args:
            body_id: Deterministic ID of the tool body

        Returns:
            Self for chaining
        """
        self.tool_body_queries.append(body_id)
        return self

    def add_target_body(self, body_id: str) -> "BooleanBuilder":
        """Add a target body by its deterministic ID.

        Target bodies are the bodies that receive the boolean operation.
        Required for SUBTRACT and INTERSECT operations.

        Args:
            body_id: Deterministic ID of the target body

        Returns:
            Self for chaining
        """
        self.target_body_queries.append(body_id)
        return self

    def build(self) -> Dict[str, Any]:
        """Build the boolean feature JSON.

        Returns:
            Feature definition for Onshape API

        Raises:
            ValueError: If required bodies are missing
        """
        if not self.tool_body_queries:
            raise ValueError("At least one tool body must be added")

        if self.boolean_type in (BooleanType.SUBTRACT, BooleanType.INTERSECT):
            if not self.target_body_queries:
                raise ValueError(
                    f"At least one target body must be added for {self.boolean_type.value} "
                    "operations"
                )

        targets_queries: List[Dict[str, Any]] = []
        if self.target_body_queries:
            targets_queries.append(
                {
                    "btType": "BTMIndividualQuery-138",
                    "deterministicIds": self.target_body_queries,
                }
            )

        parameters: List[Dict[str, Any]] = [
            {
                "btType": "BTMParameterEnum-145",
                "namespace": "",
                "enumName": "BooleanOperationType",
                "value": self.boolean_type.value,
                "parameterId": "operationType",
                "parameterName": "",
                "libraryRelationType": "NONE",
            },
            {
                "btType": "BTMParameterQueryList-148",
                "queries": [
                    {
                        "btType": "BTMIndividualQuery-138",
                        "deterministicIds": self.tool_body_queries,
                    }
                ],
                "parameterId": "tools",
                "parameterName": "",
                "libraryRelationType": "NONE",
            },
            {
                "btType": "BTMParameterQueryList-148",
                "queries": targets_queries,
                "parameterId": "targets",
                "parameterName": "",
                "libraryRelationType": "NONE",
            },
            {
                "btType": "BTMParameterBoolean-144",
                "value": False,
                "parameterId": "offset",
                "parameterName": "",
                "libraryRelationType": "NONE",
            },
            {
                "btType": "BTMParameterBoolean-144",
                "value": False,
                "parameterId": "offsetAll",
                "parameterName": "",
                "libraryRelationType": "NONE",
            },
            {
                "btType": "BTMParameterQueryList-148",
                "queries": [],
                "parameterId": "entitiesToOffset",
                "parameterName": "",
                "libraryRelationType": "NONE",
            },
            {
                "btType": "BTMParameterQuantity-147",
                "isInteger": False,
                "value": 0.0,
                "units": "",
                "expression": "0 in",
                "parameterId": "offsetDistance",
                "parameterName": "",
                "libraryRelationType": "NONE",
            },
            {
                "btType": "BTMParameterBoolean-144",
                "value": False,
                "parameterId": "oppositeDirection",
                "parameterName": "",
                "libraryRelationType": "NONE",
            },
            {
                "btType": "BTMParameterBoolean-144",
                "value": False,
                "parameterId": "reFillet",
                "parameterName": "",
                "libraryRelationType": "NONE",
            },
            {
                "btType": "BTMParameterBoolean-144",
                "value": False,
                "parameterId": "keepTools",
                "parameterName": "",
                "libraryRelationType": "NONE",
            },
        ]

        return {
            "btType": "BTFeatureDefinitionCall-1406",
            "feature": {
                "btType": "BTMFeature-134",
                "featureType": "booleanBodies",
                "name": self.name,
                "suppressed": False,
                "namespace": "",
                "parameters": parameters,
            },
        }
