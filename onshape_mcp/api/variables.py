"""Variable table management for Onshape Variable Studios."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from .client import OnshapeClient


# Common FeatureScript VariableType values
VARIABLE_TYPE_MAP = {
    "in": "LENGTH",
    "mm": "LENGTH",
    "cm": "LENGTH",
    "m": "LENGTH",
    "ft": "LENGTH",
    "deg": "ANGLE",
    "rad": "ANGLE",
}


def _infer_variable_type(expression: str) -> str:
    """Infer the FeatureScript VariableType from an expression.

    Args:
        expression: Variable expression (e.g., '0.75 in', '45 deg', '3.14')

    Returns:
        VariableType string (LENGTH, ANGLE, or ANY)
    """
    expr = expression.strip().lower()
    for suffix, var_type in VARIABLE_TYPE_MAP.items():
        if expr.endswith(suffix):
            return var_type
    return "ANY"


class Variable(BaseModel):
    """Represents a variable in an Onshape variable table."""

    name: str
    expression: str
    description: Optional[str] = None
    type: Optional[str] = None


class VariableManager:
    """Manager for Onshape variable tables."""

    def __init__(self, client: OnshapeClient):
        """Initialize the variable manager.

        Args:
            client: Onshape API client
        """
        self.client = client

    async def create_variable_studio(
        self, document_id: str, workspace_id: str, name: str
    ) -> Dict[str, Any]:
        """Create a new Variable Studio in a document.

        Args:
            document_id: Document ID
            workspace_id: Workspace ID
            name: Name for the new Variable Studio

        Returns:
            API response with new Variable Studio info
        """
        path = f"/api/variables/d/{document_id}/w/{workspace_id}/variablestudio"
        data = {"name": name}
        return await self.client.post(path, data=data)

    async def get_variables(
        self, document_id: str, workspace_id: str, element_id: str
    ) -> List[Variable]:
        """Get all variables from a Variable Studio.

        Args:
            document_id: Document ID
            workspace_id: Workspace ID
            element_id: Variable Studio element ID

        Returns:
            List of variables
        """
        path = f"/api/variables/d/{document_id}/w/{workspace_id}/e/{element_id}/variables"
        response = await self.client.get(path)

        # Response is [{variableStudioReference, variables: [...]}, ...]
        variables = []
        for group in response:
            for var_data in group.get("variables", []):
                variables.append(
                    Variable(
                        name=var_data.get("name", ""),
                        expression=var_data.get("expression", ""),
                        description=var_data.get("description"),
                        type=var_data.get("type"),
                    )
                )

        return variables

    async def set_variable(
        self,
        document_id: str,
        workspace_id: str,
        element_id: str,
        name: str,
        expression: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Set or update a variable in a Variable Studio.

        Preserves existing variables by reading them first, then sending
        the full list with the new/updated variable.

        Args:
            document_id: Document ID
            workspace_id: Workspace ID
            element_id: Variable Studio element ID
            name: Variable name
            expression: Variable expression (e.g., "0.75 in")
            description: Optional variable description

        Returns:
            API response
        """
        path = f"/api/variables/d/{document_id}/w/{workspace_id}/e/{element_id}/variables"

        # GET existing variables so we don't overwrite them
        existing = await self.client.get(path)
        variables: List[Dict[str, Any]] = []
        for group in existing:
            for var_data in group.get("variables", []):
                variables.append({
                    "name": var_data["name"],
                    "expression": var_data["expression"],
                    "type": var_data.get("type", "ANY"),
                    **({"description": var_data["description"]} if var_data.get("description") else {}),
                })

        # Update existing or append new
        var_type = _infer_variable_type(expression)
        new_var: Dict[str, Any] = {"name": name, "expression": expression, "type": var_type}
        if description:
            new_var["description"] = description

        found = False
        for i, v in enumerate(variables):
            if v["name"] == name:
                variables[i] = new_var
                found = True
                break
        if not found:
            variables.append(new_var)

        return await self.client.post(path, data=variables)

    async def get_configuration_definition(
        self, document_id: str, workspace_id: str, element_id: str
    ) -> Dict[str, Any]:
        """Get configuration definition for an element.

        Args:
            document_id: Document ID
            workspace_id: Workspace ID
            element_id: Element ID

        Returns:
            Configuration definition
        """
        path = f"/api/v6/elements/d/{document_id}/w/{workspace_id}/e/{element_id}/configuration"
        return await self.client.get(path)
