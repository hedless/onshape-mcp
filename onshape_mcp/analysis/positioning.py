"""Assembly positioning tools for absolute placement and face alignment."""

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from loguru import logger

from ..units import format_length, from_meters, to_meters
from .interference import BoundingBox, get_world_aabb

FACE_NAMES = {"front", "back", "left", "right", "top", "bottom"}


@dataclass
class InstancePositionInfo:
    """Position and extent of a single assembly instance, in the configured length unit."""

    name: str
    instance_id: str
    position_x: float
    position_y: float
    position_z: float
    size_x: float
    size_y: float
    size_z: float
    world_low_x: float
    world_low_y: float
    world_low_z: float
    world_high_x: float
    world_high_y: float
    world_high_z: float


def extract_occurrence_transforms(
    assembly_data: Dict[str, Any],
) -> Dict[str, List[float]]:
    """Extract instance_id -> transform matrix mapping from assembly data.

    Handles only top-level instances (path length == 1).

    Args:
        assembly_data: Raw assembly definition from API

    Returns:
        Dict mapping instance ID to 16-element row-major transform
    """
    occurrence_transforms: Dict[str, List[float]] = {}
    root = assembly_data.get("rootAssembly", {})
    for occ in root.get("occurrences", []):
        path = occ.get("path", [])
        if len(path) == 1:
            occurrence_transforms[path[0]] = occ.get(
                "transform",
                [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
            )
    return occurrence_transforms


def get_position_from_transform(
    transform: List[float],
) -> Tuple[float, float, float]:
    """Extract translation (meters) from a 4x4 row-major transform.

    Args:
        transform: 16-element row-major matrix

    Returns:
        (tx, ty, tz) in meters
    """
    return (transform[3], transform[7], transform[11])


def build_absolute_translation_matrix(x: float, y: float, z: float) -> List[float]:
    """Build a 4x4 identity-rotation matrix with given translation.

    Args:
        x: X position in the configured length unit
        y: Y position in the configured length unit
        z: Z position in the configured length unit

    Returns:
        16-element row-major 4x4 matrix
    """
    return [
        1.0,
        0.0,
        0.0,
        to_meters(x),
        0.0,
        1.0,
        0.0,
        to_meters(y),
        0.0,
        0.0,
        1.0,
        to_meters(z),
        0.0,
        0.0,
        0.0,
        1.0,
    ]


def compute_aligned_position(
    source_local_bbox: BoundingBox,
    source_current_pos_meters: Tuple[float, float, float],
    target_world_aabb: BoundingBox,
    face: str,
) -> Tuple[float, float, float]:
    """Compute new absolute position (meters) for source to be flush against target face.

    The source is placed OUTSIDE the target, touching the specified face.
    Only the axis perpendicular to the face changes; other axes are preserved.

    Args:
        source_local_bbox: Source part's local bounding box (meters)
        source_current_pos_meters: Source's current (tx, ty, tz) in meters
        target_world_aabb: Target's world-space AABB (meters)
        face: One of "front", "back", "left", "right", "top", "bottom"

    Returns:
        (new_x, new_y, new_z) in meters

    Raises:
        ValueError: If face is not a valid face name
    """
    if face not in FACE_NAMES:
        raise ValueError(f"Invalid face '{face}'. Must be one of: {sorted(FACE_NAMES)}")

    cur_x, cur_y, cur_z = source_current_pos_meters

    if face == "front":
        new_y = target_world_aabb.low_y - source_local_bbox.high_y
        return (cur_x, new_y, cur_z)
    elif face == "back":
        new_y = target_world_aabb.high_y - source_local_bbox.low_y
        return (cur_x, new_y, cur_z)
    elif face == "left":
        new_x = target_world_aabb.low_x - source_local_bbox.high_x
        return (new_x, cur_y, cur_z)
    elif face == "right":
        new_x = target_world_aabb.high_x - source_local_bbox.low_x
        return (new_x, cur_y, cur_z)
    elif face == "bottom":
        new_z = target_world_aabb.low_z - source_local_bbox.high_z
        return (cur_x, cur_y, new_z)
    else:  # top
        new_z = target_world_aabb.high_z - source_local_bbox.low_z
        return (cur_x, cur_y, new_z)


def format_positions_report(positions: List[InstancePositionInfo]) -> str:
    """Format instance positions into human-readable text.

    Args:
        positions: List of position info for each instance

    Returns:
        Formatted string for MCP tool response
    """
    lines = ["Assembly Instance Positions", "=" * 40, ""]

    if not positions:
        lines.append("No instances found in assembly.")
        return "\n".join(lines)

    lines.append(f"Found {len(positions)} instance(s):\n")

    for p in positions:
        lines.append(f"**{p.name}** (ID: {p.instance_id})")
        lines.append(
            f"  Position: X={format_length(p.position_x)}, "
            f"Y={format_length(p.position_y)}, "
            f"Z={format_length(p.position_z)}"
        )
        lines.append(
            f"  Size: {format_length(p.size_x)} W x "
            f"{format_length(p.size_y)} D x "
            f"{format_length(p.size_z)} H"
        )
        lines.append(
            f"  World bounds: "
            f"X=[{format_length(p.world_low_x)}, {format_length(p.world_high_x)}], "
            f"Y=[{format_length(p.world_low_y)}, {format_length(p.world_high_y)}], "
            f"Z=[{format_length(p.world_low_z)}, {format_length(p.world_high_z)}]"
        )
        lines.append("")

    return "\n".join(lines)


async def get_assembly_positions(
    assembly_manager,
    partstudio_manager,
    document_id: str,
    workspace_id: str,
    element_id: str,
) -> str:
    """Fetch and format all instance positions in an assembly.

    Args:
        assembly_manager: AssemblyManager instance
        partstudio_manager: PartStudioManager instance
        document_id: Document ID
        workspace_id: Workspace ID
        element_id: Assembly element ID

    Returns:
        Formatted position report string
    """
    assembly_data = await assembly_manager.get_assembly_definition(
        document_id, workspace_id, element_id
    )
    root = assembly_data.get("rootAssembly", {})
    instances = root.get("instances", [])
    occ_transforms = extract_occurrence_transforms(assembly_data)
    identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]

    # Fetch bounding boxes, cached by unique part
    bbox_cache: Dict[tuple, BoundingBox] = {}
    for inst in instances:
        if inst.get("type") != "Part" or inst.get("suppressed", False):
            continue
        inst_doc_id = inst.get("documentId", document_id)
        inst_elem_id = inst.get("elementId")
        inst_part_id = inst.get("partId")
        if not inst_elem_id or not inst_part_id:
            continue
        cache_key = (inst_doc_id, inst_elem_id, inst_part_id)
        if cache_key not in bbox_cache:
            try:
                bbox_data = await partstudio_manager.get_part_bounding_box(
                    inst_doc_id, workspace_id, inst_elem_id, inst_part_id
                )
                bbox_cache[cache_key] = BoundingBox.from_api_response(bbox_data)
            except Exception as e:
                logger.warning(f"Could not get bbox for part {inst_part_id}: {e}")

    # Build position info for each instance
    positions: List[InstancePositionInfo] = []
    for inst in instances:
        if inst.get("type") != "Part" or inst.get("suppressed", False):
            continue
        inst_doc_id = inst.get("documentId", document_id)
        inst_elem_id = inst.get("elementId")
        inst_part_id = inst.get("partId")
        cache_key = (inst_doc_id, inst_elem_id, inst_part_id)
        if cache_key not in bbox_cache:
            continue

        transform = occ_transforms.get(inst["id"], identity)
        pos_meters = get_position_from_transform(transform)
        local_bbox = bbox_cache[cache_key]
        world_bbox = get_world_aabb(local_bbox, transform)

        positions.append(
            InstancePositionInfo(
                name=inst.get("name", "Unnamed"),
                instance_id=inst["id"],
                position_x=from_meters(pos_meters[0]),
                position_y=from_meters(pos_meters[1]),
                position_z=from_meters(pos_meters[2]),
                size_x=from_meters(world_bbox.high_x - world_bbox.low_x),
                size_y=from_meters(world_bbox.high_y - world_bbox.low_y),
                size_z=from_meters(world_bbox.high_z - world_bbox.low_z),
                world_low_x=from_meters(world_bbox.low_x),
                world_low_y=from_meters(world_bbox.low_y),
                world_low_z=from_meters(world_bbox.low_z),
                world_high_x=from_meters(world_bbox.high_x),
                world_high_y=from_meters(world_bbox.high_y),
                world_high_z=from_meters(world_bbox.high_z),
            )
        )

    return format_positions_report(positions)


async def set_absolute_position(
    assembly_manager,
    document_id: str,
    workspace_id: str,
    element_id: str,
    instance_id: str,
    x: float,
    y: float,
    z: float,
) -> str:
    """Set an instance to an absolute position.

    Args:
        assembly_manager: AssemblyManager instance
        document_id: Document ID
        workspace_id: Workspace ID
        element_id: Assembly element ID
        instance_id: Instance to position
        x: Absolute X position in the configured length unit
        y: Absolute Y position in the configured length unit
        z: Absolute Z position in the configured length unit

    Returns:
        Confirmation message string
    """
    transform = build_absolute_translation_matrix(x, y, z)
    occurrences = [{"path": [instance_id], "transform": transform}]
    await assembly_manager.transform_occurrences(
        document_id, workspace_id, element_id, occurrences, is_relative=False
    )
    return (
        f"Set instance {instance_id} to absolute position: "
        f"X={format_length(x)}, Y={format_length(y)}, Z={format_length(z)}"
    )


async def align_to_face(
    assembly_manager,
    partstudio_manager,
    document_id: str,
    workspace_id: str,
    element_id: str,
    source_instance_id: str,
    target_instance_id: str,
    face: str,
) -> str:
    """Align source instance flush against a face of the target instance.

    Args:
        assembly_manager: AssemblyManager instance
        partstudio_manager: PartStudioManager instance
        document_id: Document ID
        workspace_id: Workspace ID
        element_id: Assembly element ID
        source_instance_id: Instance ID to move
        target_instance_id: Instance ID to align against
        face: Face of target ("front"/"back"/"left"/"right"/"top"/"bottom")

    Returns:
        Confirmation message with new position

    Raises:
        ValueError: If face is invalid or instances not found
    """
    face = face.lower().strip()
    if face not in FACE_NAMES:
        raise ValueError(f"Invalid face '{face}'. Must be one of: {sorted(FACE_NAMES)}")

    assembly_data = await assembly_manager.get_assembly_definition(
        document_id, workspace_id, element_id
    )
    root = assembly_data.get("rootAssembly", {})
    instances = root.get("instances", [])
    occ_transforms = extract_occurrence_transforms(assembly_data)
    identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]

    # Find source and target instances
    source_inst = None
    target_inst = None
    for inst in instances:
        if inst["id"] == source_instance_id:
            source_inst = inst
        if inst["id"] == target_instance_id:
            target_inst = inst

    if source_inst is None:
        raise ValueError(f"Source instance '{source_instance_id}' not found in assembly")
    if target_inst is None:
        raise ValueError(f"Target instance '{target_instance_id}' not found in assembly")

    # Get bounding boxes
    def _bbox_params(inst):
        return (
            inst.get("documentId", document_id),
            inst.get("elementId"),
            inst.get("partId"),
        )

    s_doc, s_elem, s_part = _bbox_params(source_inst)
    t_doc, t_elem, t_part = _bbox_params(target_inst)

    source_bbox_data = await partstudio_manager.get_part_bounding_box(
        s_doc, workspace_id, s_elem, s_part
    )
    source_local_bbox = BoundingBox.from_api_response(source_bbox_data)

    target_bbox_data = await partstudio_manager.get_part_bounding_box(
        t_doc, workspace_id, t_elem, t_part
    )
    target_local_bbox = BoundingBox.from_api_response(target_bbox_data)

    # Compute target world AABB and source current position
    target_transform = occ_transforms.get(target_instance_id, identity)
    target_world_aabb = get_world_aabb(target_local_bbox, target_transform)

    source_transform = occ_transforms.get(source_instance_id, identity)
    source_current_pos = get_position_from_transform(source_transform)

    # Compute new position
    new_pos_meters = compute_aligned_position(
        source_local_bbox, source_current_pos, target_world_aabb, face
    )

    new_x = from_meters(new_pos_meters[0])
    new_y = from_meters(new_pos_meters[1])
    new_z = from_meters(new_pos_meters[2])

    # Apply absolute transform
    transform = build_absolute_translation_matrix(new_x, new_y, new_z)
    occurrences = [{"path": [source_instance_id], "transform": transform}]
    await assembly_manager.transform_occurrences(
        document_id, workspace_id, element_id, occurrences, is_relative=False
    )

    return (
        f"Aligned '{source_inst.get('name', source_instance_id)}' to "
        f"'{face}' face of '{target_inst.get('name', target_instance_id)}'.\n"
        f"New position: X={format_length(new_x)}, Y={format_length(new_y)}, "
        f"Z={format_length(new_z)}"
    )
