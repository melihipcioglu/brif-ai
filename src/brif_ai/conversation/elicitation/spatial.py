"""Deterministic validation and node grounding for structured spatial relationship proposals."""

from __future__ import annotations

from typing import TYPE_CHECKING

from brif_ai.brief.models.common import Priority
from brif_ai.spatial.models import (
    ProposedSpatialRelationship,
    RelationshipProvenance,
    SpatialNode,
    SpatialRelationType,
    project_space_requests_to_spatial_nodes,
)

if TYPE_CHECKING:
    from brif_ai.brief.models.snapshot import BriefSnapshot


def validate_and_ground_spatial_proposals(
    proposals: list[ProposedSpatialRelationship],
    snapshot: BriefSnapshot | None,
) -> list[ProposedSpatialRelationship]:
    """Validate and ground structured LLM spatial proposals against authoritative nodes.

    Zero free-text regex keyword parsing.
    Validates:
    - Snapshot presence and space request existence
    - Node existence against projected authoritative SpatialNodes
    - Resolves SpaceRequest-level IDs (e.g. sr_bed) to discrete SpatialNodes when unambiguous
    - Source != Target
    - Provenance validity (USER_STATED or AI_INFERRED)
    - Enforces requires_user_confirmation=True
    """
    if snapshot is None or not snapshot.space_requests or not proposals:
        return []

    valid_nodes = project_space_requests_to_spatial_nodes(snapshot.space_requests)
    valid_node_ids = {node.id for node in valid_nodes}
    nodes_by_req: dict[str, list[SpatialNode]] = {}
    for node in valid_nodes:
        nodes_by_req.setdefault(node.source_space_request_id, []).append(node)

    grounded: list[ProposedSpatialRelationship] = []

    for prop in proposals:
        src_id = prop.source_space_id
        tgt_id = prop.target_space_id

        # Direct matching to valid discrete spatial node IDs
        if src_id in valid_node_ids and tgt_id in valid_node_ids:
            if src_id == tgt_id:
                continue
            grounded.append(
                prop.model_copy(
                    update={
                        "provenance": (
                            prop.provenance
                            if prop.provenance
                            in (
                                RelationshipProvenance.USER_STATED,
                                RelationshipProvenance.AI_INFERRED,
                            )
                            else RelationshipProvenance.USER_STATED
                        ),
                        "priority": prop.priority
                        if isinstance(prop.priority, Priority)
                        else Priority.MUST,
                        "requires_user_confirmation": True,
                    }
                )
            )
            continue

        # Handle SpaceRequest ID referencing (e.g. LLM used 'sr_bed' for multi-instance room)
        if src_id == tgt_id and src_id in nodes_by_req:
            req_nodes = nodes_by_req[src_id]
            if len(req_nodes) >= 2:
                grounded.append(
                    prop.model_copy(
                        update={
                            "source_space_id": req_nodes[0].id,
                            "target_space_id": req_nodes[1].id,
                            "provenance": (
                                prop.provenance
                                if prop.provenance
                                in (
                                    RelationshipProvenance.USER_STATED,
                                    RelationshipProvenance.AI_INFERRED,
                                )
                                else RelationshipProvenance.USER_STATED
                            ),
                            "priority": prop.priority
                            if isinstance(prop.priority, Priority)
                            else Priority.MUST,
                            "requires_user_confirmation": True,
                        }
                    )
                )
                continue

        # Handle SpaceRequest IDs for distinct spaces (e.g. LLM used 'sr_kitchen' and 'sr_living')
        resolved_src = (
            nodes_by_req[src_id][0].id
            if src_id in nodes_by_req and nodes_by_req[src_id]
            else (src_id if src_id in valid_node_ids else None)
        )
        resolved_tgt = (
            nodes_by_req[tgt_id][0].id
            if tgt_id in nodes_by_req and nodes_by_req[tgt_id]
            else (tgt_id if tgt_id in valid_node_ids else None)
        )

        if resolved_src is not None and resolved_tgt is not None and resolved_src != resolved_tgt:
            grounded.append(
                prop.model_copy(
                    update={
                        "source_space_id": resolved_src,
                        "target_space_id": resolved_tgt,
                        "provenance": (
                            prop.provenance
                            if prop.provenance
                            in (
                                RelationshipProvenance.USER_STATED,
                                RelationshipProvenance.AI_INFERRED,
                            )
                            else RelationshipProvenance.USER_STATED
                        ),
                        "priority": prop.priority
                        if isinstance(prop.priority, Priority)
                        else Priority.MUST,
                        "requires_user_confirmation": True,
                    }
                )
            )

    return grounded


def format_spatial_relationship_statement(
    proposal: ProposedSpatialRelationship,
    snapshot: BriefSnapshot,
) -> str:
    """Format clear Turkish confirmation message for a spatial relationship proposal."""
    nodes = project_space_requests_to_spatial_nodes(snapshot.space_requests)
    node_map = {node.id: node.display_name for node in nodes}

    src_name = node_map.get(proposal.source_space_id, proposal.source_space_id)
    tgt_name = node_map.get(proposal.target_space_id, proposal.target_space_id)

    rel_descriptions = {
        SpatialRelationType.ADJACENT_TO: (
            f"{src_name} ile {tgt_name} yan yana / bitişik olacak şekilde planlanmalıdır."
        ),
        SpatialRelationType.NEAR: (
            f"{src_name} ile {tgt_name} birbirine yakın olacak şekilde konumlandırılmalıdır."
        ),
        SpatialRelationType.SEPARATED_FROM: (
            f"{src_name} ile {tgt_name} birbirinden ayrışmış/uzak olacak şekilde planlanmalıdır."
        ),
        SpatialRelationType.VISUAL_CONNECTION: (
            f"{src_name} ile {tgt_name} arasında görsel bağlantı kurulmalıdır."
        ),
        SpatialRelationType.DIRECT_ACCESS: (
            f"{src_name} ile {tgt_name} arasında doğrudan geçiş sağlanmalıdır."
        ),
        SpatialRelationType.INDIRECT_ACCESS: (
            f"{src_name} ile {tgt_name} arasında dolaylı erişim sağlanmalıdır."
        ),
        SpatialRelationType.ACOUSTIC_SEPARATION: (
            f"{src_name} ile {tgt_name} arasında ses yalıtımı sağlanmalıdır."
        ),
        SpatialRelationType.PRIVACY_SEPARATION: (
            f"{src_name} ile {tgt_name} arasında mahremiyet ayrımı sağlanmalıdır."
        ),
    }

    desc = rel_descriptions.get(
        proposal.relation_type,
        f"{src_name} ile {tgt_name} arasında {proposal.relation_type.value} ilişkisi tanımlandı.",
    )
    return f"{desc} Bu mekânsal ilişkiyi onaylıyor musunuz?"
