"""Read-only metadata, configuration, and BOM access.

Pulls product data (part numbers, names, descriptions, configured property
values, and assembly BOMs) straight from Onshape, for reconciling CAD against
an ERP, a catalog, or documentation. Nothing here writes to Onshape.
"""

import itertools
from typing import Any, Dict, List, Optional

from .client import OnshapeClient


class MetadataManager:
    """Read-only Onshape metadata, configuration, and BOM access."""

    def __init__(self, client: OnshapeClient):
        """Initialize the metadata manager.

        Args:
            client: Onshape API client
        """
        self.client = client

    async def get_element_metadata(
        self,
        document_id: str,
        wvm: str,
        wvm_id: str,
        element_id: str,
        configuration: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get an element's metadata and its parts' properties.

        Args:
            document_id: Document ID
            wvm: 'w' (workspace), 'v' (version), or 'm' (microversion)
            wvm_id: Workspace, version, or microversion ID
            element_id: Element ID
            configuration: Optional encoded configuration string

        Returns:
            Metadata with properties keyed by display name (Part number, Name, ...)
        """
        params: Dict[str, Any] = {"depth": 1, "includePropertyDefaults": "true"}
        if configuration:
            params["configuration"] = configuration
        path = f"/api/v6/metadata/d/{document_id}/{wvm}/{wvm_id}/e/{element_id}"
        return await self.client.get(path, params=params)

    async def get_part_metadata(
        self,
        document_id: str,
        wvm: str,
        wvm_id: str,
        element_id: str,
        part_id: str,
        configuration: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get the properties of a single part (Part number, Description, ...)."""
        params: Dict[str, Any] = {"includePropertyDefaults": "true"}
        if configuration:
            params["configuration"] = configuration
        path = f"/api/v6/metadata/d/{document_id}/{wvm}/{wvm_id}/e/{element_id}/p/{part_id}"
        return await self.client.get(path, params=params)

    async def get_assembly_bom(
        self,
        document_id: str,
        wvm: str,
        wvm_id: str,
        element_id: str,
        indented: bool = True,
        configuration: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get an assembly's Bill of Materials.

        Use wvm='v' with a released version ID for the production BOM.
        """
        params: Dict[str, Any] = {
            "indented": str(indented).lower(),
            "multiLevel": "true",
            "generateIfAbsent": "true",
        }
        if configuration:
            params["configuration"] = configuration
        path = f"/api/v6/assemblies/d/{document_id}/{wvm}/{wvm_id}/e/{element_id}/bom"
        return await self.client.get(path, params=params)

    @staticmethod
    def flatten_bom_rows(bom: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Turn a BOM response into rows keyed by column name instead of header ID."""
        headers = {
            h.get("id", h.get("propertyId")): h.get("name") for h in bom.get("headers") or []
        }
        rows = []
        for row in bom.get("rows") or []:
            values = row.get("headerIdToValue", row)
            if not isinstance(values, dict):
                continue
            record = {}
            for key, value in values.items():
                if isinstance(value, dict) and "displayName" in value:
                    value = value["displayName"]
                record[headers.get(key, key)] = value
            rows.append(record)
        return rows

    async def get_configuration(
        self, document_id: str, wvm: str, wvm_id: str, element_id: str
    ) -> Dict[str, Any]:
        """Get an element's configuration inputs, their types, and allowed options.

        Works for assemblies and Part Studios. One API call.
        """
        path = f"/api/v6/elements/d/{document_id}/{wvm}/{wvm_id}/e/{element_id}/configuration"
        return await self.client.get(path)

    @staticmethod
    def parse_config_params(definition: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Flatten a configuration definition into [{id, name, type, options}].

        Accepts both the wrapped ({"message": {...}}) and flat parameter shapes.
        """
        params = []
        for raw in definition.get("configurationParameters") or []:
            msg = raw.get("message", raw)
            type_name = (
                raw.get("typeName") or raw.get("btType") or msg.get("typeName") or ""
            ).lower()
            options = []
            for raw_option in msg.get("options") or []:
                option = raw_option.get("message", raw_option)
                options.append(
                    {
                        "value": option.get("option"),
                        "name": option.get("optionName", option.get("option")),
                    }
                )
            if "enum" in type_name or options:
                param_type = "enum"
            elif "boolean" in type_name:
                param_type = "boolean"
            elif "quantity" in type_name:
                param_type = "quantity"
            else:
                param_type = "string"
            params.append(
                {
                    "id": msg.get("parameterId"),
                    "name": msg.get("parameterName", msg.get("parameterId")),
                    "type": param_type,
                    "options": options,
                }
            )
        return params

    async def get_configured_properties(
        self,
        document_id: str,
        wvm: str,
        wvm_id: str,
        element_id: str,
        max_variants: int = 48,
    ) -> Dict[str, Any]:
        """Get resolved properties for every configuration variant of an element.

        Expands every combination of enum inputs and reads the element's metadata
        once per combination, so it costs 1 + N API calls for N variants. If N
        would exceed max_variants, returns a warning and the parameters instead
        of making the calls.
        """
        definition = await self.get_configuration(document_id, wvm, wvm_id, element_id)
        params = self.parse_config_params(definition)
        enum_params = [p for p in params if p["type"] == "enum" and p["options"]]

        total = 1
        for p in enum_params:
            total *= len(p["options"])
        if total > max_variants:
            return {
                "_warning": (
                    f"{total} variants would need {total} metadata calls, over the "
                    f"max_variants cap ({max_variants}). Raise max_variants to proceed."
                ),
                "variant_count": total,
                "parameters": params,
            }

        option_lists = [
            [(p["id"], o["value"], p["name"], o["name"]) for o in p["options"]] for p in enum_params
        ]
        variants = []
        for combo in itertools.product(*option_lists):
            configuration = ";".join(f"{pid}={value}" for pid, value, _, _ in combo) or None
            meta = await self.get_element_metadata(
                document_id, wvm, wvm_id, element_id, configuration=configuration
            )
            properties = {p.get("name"): p.get("value") for p in meta.get("properties") or []}
            variants.append(
                {
                    "configuration": {pname: oname for _, _, pname, oname in combo},
                    "properties": properties,
                }
            )
        return {"parameters": params, "variant_count": len(variants), "variants": variants}
