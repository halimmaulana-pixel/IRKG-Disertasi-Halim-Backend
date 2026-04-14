# backend/routers/graph.py
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from database import get_db
from models import KGNode, KGEdge, AcceptedMapping, CRIResult
from typing import Optional

router = APIRouter()

ESCO_URI_PREFIX = "http://data.europa.eu/esco/skill/"


def _normalize_target_id(node_id: str, target_type: Optional[str] = None) -> str:
    raw = str(node_id or "").strip()
    if not raw:
        return raw
    if target_type == "ESCO" and not raw.startswith(ESCO_URI_PREFIX):
        return f"{ESCO_URI_PREFIX}{raw}"
    return raw


def _resolve_node(node_id: str, db: Session, target_type: Optional[str] = None):
    raw = str(node_id or "").strip()
    if not raw:
        return None
    node = db.query(KGNode).filter(KGNode.id == raw).first()
    if node:
        return node
    normalized = _normalize_target_id(raw, target_type)
    if normalized != raw:
        return db.query(KGNode).filter(KGNode.id == normalized).first()
    return None


def _mapping_target_id(mapping: AcceptedMapping) -> str:
    return _normalize_target_id(mapping.target_id, mapping.target_type)


def _short_node_id(node_id: str) -> str:
    raw = str(node_id or "").strip()
    if not raw:
        return raw
    return raw.rsplit("/", 1)[-1]


def node_to_cyto(node: KGNode, extra_data: dict = {}) -> dict:
    """Convert KGNode ke format Cytoscape.js element"""
    colors = {
        "CPL": "#003d7a",
        "ESCO_SKILL": "#0891b2",
        "ONET": "#059669",
        "SKKNI": "#d97706",
        "ESCO_OCC": "#7c3aed",
    }
    return {
        "data": {
            "id": node.id,
            "label": node.label[:40] + "..." if len(node.label) > 40 else node.label,
            "full_label": node.label,
            "short_id": _short_node_id(node.id),
            "type": node.node_type,
            "node_type": node.node_type,
            "description": node.description,
            "color": colors.get(node.node_type, "#666666"),
            **extra_data
        }
    }

def edge_to_cyto(edge: KGEdge) -> dict:
    """Convert KGEdge ke format Cytoscape.js element"""
    edge_colors = {
        "MAPS_TO": "#c8972a",
        "BROADER": "#94a3b8",
        "RELATED": "#64748b",
        "CROSSWALK": "#ec4899",
    }
    return {
        "data": {
            "id": f"e_{edge.id}",
            "source": edge.source_id,
            "target": edge.target_id,
            "type": edge.edge_type,
            "edge_type": edge.edge_type,
            "weight": edge.weight,
            "color": edge_colors.get(edge.edge_type, "#999"),
            "width": max(1, int(edge.weight * 5)) if edge.weight else 1,
        }
    }


def mapping_to_cyto(mapping: AcceptedMapping, cfg: str) -> dict:
    normalized_target_id = _mapping_target_id(mapping)
    return {
        "data": {
            "id": f"maps_{mapping.id}_{cfg}",
            "source": mapping.source_id,
            "target": normalized_target_id,
            "type": "MAPS_TO",
            "edge_type": "MAPS_TO",
            "target_type": mapping.target_type,
            "weight": mapping.s_final,
            "color": "#c8972a",
            "width": max(1, int(mapping.s_final * 6)) if mapping.s_final else 1,
            "s_sem": round(mapping.s_sem, 4) if mapping.s_sem is not None else None,
            "s_gr": round(mapping.s_gr, 4) if mapping.s_gr is not None else None,
            "s_con": round(mapping.s_con, 4) if mapping.s_con is not None else None,
        }
    }


def _node_or_dummy(node_id: str, db: Session, fallback_type: str = "UNKNOWN"):
    node = _resolve_node(node_id, db, fallback_type)
    if node:
        return node
    normalized = _normalize_target_id(node_id, fallback_type)
    return KGNode(id=normalized, label=normalized, node_type=fallback_type, description="")

@router.get("/ego/{node_id}")
def get_ego_graph(
    node_id: str,
    depth: int = Query(1, ge=1, le=2),
    max_nodes: int = Query(40, ge=5, le=100),
    edge_types: Optional[str] = Query(None),
    min_weight: float = Query(0.0, ge=0.0, le=1.0),
    config: str = Query("v1.2"),
    db: Session = Depends(get_db)
):
    """Ambil ego-graph 1-2 hop dari node_id"""
    visited_ids = set()
    visited_edges = set()
    all_nodes = []
    all_edges = []

    allowed_types = edge_types.split(",") if edge_types else None

    def get_neighbors(nid: str, current_depth: int):
        if current_depth > depth or len(visited_ids) >= max_nodes:
            return

        budget = max(1, max_nodes - len(visited_ids))
        edge_payloads = []

        # Structural edges from kg_edges (incoming + outgoing)
        q = db.query(KGEdge).filter((KGEdge.source_id == nid) | (KGEdge.target_id == nid))
        if allowed_types:
            q = q.filter(KGEdge.edge_type.in_(allowed_types))
        if min_weight > 0:
            q = q.filter((KGEdge.weight == None) | (KGEdge.weight >= min_weight))
        if config:
            q = q.filter((KGEdge.config == config) | (KGEdge.config == None))
        for edge in q.limit(budget).all():
            edge_payloads.append(edge_to_cyto(edge))

        # MAPS_TO fallback per config from accepted_mappings
        include_maps = (allowed_types is None) or ("MAPS_TO" in allowed_types)
        if include_maps and config:
            mq = db.query(AcceptedMapping).filter(
                AcceptedMapping.config == config,
                AcceptedMapping.forced_top1 == False,
                or_(AcceptedMapping.source_id == nid, AcceptedMapping.target_id == nid),
            )
            if min_weight > 0:
                mq = mq.filter(AcceptedMapping.s_final >= min_weight)
            for m in mq.limit(budget).all():
                edge_payloads.append(mapping_to_cyto(m, config))

        for e in edge_payloads:
            src = e["data"]["source"]
            tgt = e["data"]["target"]
            eid = e["data"]["id"]
            neighbor_id = tgt if src == nid else src
            if eid not in visited_edges:
                all_edges.append(e)
                visited_edges.add(eid)
            if neighbor_id not in visited_ids:
                neighbor_type = None
                if neighbor_id == tgt and src == nid:
                    neighbor_type = e["data"].get("target_type")
                neighbor_node = _resolve_node(neighbor_id, db, neighbor_type)
                if neighbor_node:
                    neighbor_id = neighbor_node.id
                    visited_ids.add(neighbor_id)
                    all_nodes.append(node_to_cyto(neighbor_node))
                    if current_depth < depth:
                        get_neighbors(neighbor_id, current_depth + 1)

    # Tambah center node
    center = db.query(KGNode).filter(KGNode.id == node_id).first()
    if not center:
        return {"nodes": [], "edges": [], "error": f"Node {node_id} not found"}

    visited_ids.add(node_id)
    extra = {}
    cri = db.query(CRIResult).filter(CRIResult.source_id == node_id).first()
    if cri:
        extra = {"cri_score": cri.cri_score, "cri_flag": cri.cri_flag}
    all_nodes.insert(0, node_to_cyto(center, {**extra, "is_center": True}))

    get_neighbors(node_id, 1)

    return {
        "nodes": all_nodes,
        "edges": all_edges,
        "center_id": node_id,
        "total_nodes": len(all_nodes),
        "total_edges": len(all_edges),
    }

@router.get("/search")
def search_nodes(
    q: str = Query(..., min_length=2),
    node_type: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Search node by label untuk searchbox di KG Explorer."""
    query = db.query(KGNode).filter(KGNode.label.ilike(f"%{q}%"))
    if node_type:
        query = query.filter(KGNode.node_type == node_type)
    nodes = query.limit(limit).all()
    return [{"id": n.id, "label": n.label, "type": n.node_type} for n in nodes]

@router.get("/cpl-subgraph/{prodi}")
def get_cpl_subgraph(
    prodi: str,
    config: str = Query("v1.2"),
    db: Session = Depends(get_db)
):
    """Ambil full subgraph untuk satu prodi"""
    mappings = db.query(AcceptedMapping).filter(
        AcceptedMapping.source_id.like(f"{prodi}_%"),
        AcceptedMapping.config == config,
        AcceptedMapping.forced_top1 == False,
    ).all()

    node_ids = set()
    all_nodes = []
    all_edges = []

    # Tambah CPL nodes
    cri_items = db.query(CRIResult).filter(CRIResult.prodi == prodi).all()

    for cri in cri_items:
        node = KGNode(
            id=cri.source_id,
            label=cri.source_id,
            node_type="CPL",
            description="",
        )
        all_nodes.append(node_to_cyto(node, {
            "cri_score": cri.cri_score,
            "cri_flag": cri.cri_flag,
            "ranah": cri.ranah,
        }))
        node_ids.add(cri.source_id)

    # Tambah target nodes + edges
    for m in mappings:
        normalized_target_id = _mapping_target_id(m)
        if normalized_target_id not in node_ids:
            target = _resolve_node(m.target_id, db, m.target_type)
            if target:
                all_nodes.append(node_to_cyto(target))
                node_ids.add(target.id)
        # Tambah edge
        all_edges.append({
            "data": {
                "id": f"maps_{m.id}",
                "source": m.source_id,
                "target": normalized_target_id,
                "type": "MAPS_TO",
                "edge_type": "MAPS_TO",
                "s_final": m.s_final,
                "target_type": m.target_type,
                "color": "#c8972a",
                "width": max(1, int(m.s_final * 6)),
            }
        })

    return {
        "nodes": all_nodes[:200],
        "edges": all_edges[:500],
        "prodi": prodi,
        "config": config,
    }


@router.get("/story/{source_id}")
def get_story_path(
    source_id: str,
    config: str = Query("v1.2"),
    target_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Story mode: tampilkan jalur mapping utama CPL + penjelasan singkat.
    """
    q = db.query(AcceptedMapping).filter(
        AcceptedMapping.source_id == source_id,
        AcceptedMapping.config == config,
        AcceptedMapping.forced_top1 == False,
    )
    if target_type:
        q = q.filter(AcceptedMapping.target_type == target_type)

    mappings = q.order_by(AcceptedMapping.s_final.desc()).limit(6).all()
    if not mappings:
        raise HTTPException(404, f"Tidak ada story path untuk {source_id} di config {config}")

    source_node = _node_or_dummy(source_id, db, fallback_type="CPL")
    nodes = [node_to_cyto(source_node, {"is_center": True})]
    edges = []
    narratives = []

    seen_targets = set()
    for idx, m in enumerate(mappings, start=1):
        normalized_target_id = _mapping_target_id(m)
        if normalized_target_id in seen_targets:
            continue
        seen_targets.add(normalized_target_id)
        target_node = _node_or_dummy(m.target_id, db, fallback_type=m.target_type)
        nodes.append(node_to_cyto(target_node, {"rank": idx, "score": round(m.s_final, 4)}))
        edges.append({
            "data": {
                "id": f"story_{source_id}_{normalized_target_id}_{idx}",
                "source": source_id,
                "target": normalized_target_id,
                "type": "MAPS_TO",
                "edge_type": "MAPS_TO",
                "weight": m.s_final,
                "s_sem": round(m.s_sem, 4),
                "s_gr": round(m.s_gr, 4),
                "s_con": round(m.s_con, 4),
                "label": f"rank #{idx}",
            }
        })
        narratives.append(
            f"Rank {idx}: '{m.target_label}' dipilih karena S_final {m.s_final:.3f} "
            f"(S_sem {m.s_sem:.3f}, S_gr {m.s_gr:.3f}, S_con {m.s_con:.3f})."
        )

    return {
        "source_id": source_id,
        "config": config,
        "target_type_filter": target_type,
        "nodes": nodes,
        "edges": edges,
        "narratives": narratives,
    }


@router.get("/delta/{source_id}")
def get_config_delta(
    source_id: str,
    config_a: str = Query("v1.2"),
    config_b: str = Query("v1.4"),
    db: Session = Depends(get_db),
):
    """
    Compare delta mapping antara dua konfigurasi untuk satu source node.
    """
    q_a = db.query(AcceptedMapping).filter(
        AcceptedMapping.source_id == source_id,
        AcceptedMapping.config == config_a,
        AcceptedMapping.forced_top1 == False,
    ).all()
    q_b = db.query(AcceptedMapping).filter(
        AcceptedMapping.source_id == source_id,
        AcceptedMapping.config == config_b,
        AcceptedMapping.forced_top1 == False,
    ).all()

    map_a = {_mapping_target_id(m): m for m in q_a}
    map_b = {_mapping_target_id(m): m for m in q_b}
    target_ids = sorted(set(map_a.keys()) | set(map_b.keys()))

    items = []
    for tid in target_ids:
        a = map_a.get(tid)
        b = map_b.get(tid)
        s_a = a.s_final if a else 0.0
        s_b = b.s_final if b else 0.0
        delta = s_b - s_a
        ref = b or a
        items.append({
            "target_id": tid,
            "target_label": ref.target_label if ref else tid,
            "target_type": ref.target_type if ref else None,
            "score_a": round(s_a, 4),
            "score_b": round(s_b, 4),
            "delta": round(delta, 4),
            "status": "gain" if delta > 0 else ("drop" if delta < 0 else "same"),
        })

    items.sort(key=lambda x: abs(x["delta"]), reverse=True)
    return {
        "source_id": source_id,
        "config_a": config_a,
        "config_b": config_b,
        "summary": {
            "n_gain": sum(1 for x in items if x["delta"] > 0),
            "n_drop": sum(1 for x in items if x["delta"] < 0),
            "n_same": sum(1 for x in items if x["delta"] == 0),
        },
        "items": items[:50],
    }


@router.get("/delta-summary")
def get_delta_summary(
    prodi: str = Query("SI"),
    config_a: str = Query("v1.2"),
    config_b: str = Query("v1.4"),
    db: Session = Depends(get_db),
):
    """
    Ringkasan delta antar config untuk seluruh CPL dalam satu prodi.
    """
    source_ids = [
        x[0] for x in db.query(AcceptedMapping.source_id).filter(
            AcceptedMapping.source_id.like(f"{prodi}_%"),
            AcceptedMapping.config.in_([config_a, config_b]),
            AcceptedMapping.forced_top1 == False,
        ).distinct().all()
    ]
    if not source_ids:
        return {"prodi": prodi, "config_a": config_a, "config_b": config_b, "items": []}

    deltas = []
    for sid in source_ids:
        agg_a = db.query(func.avg(AcceptedMapping.s_final)).filter(
            AcceptedMapping.source_id == sid, AcceptedMapping.config == config_a, AcceptedMapping.forced_top1 == False
        ).scalar() or 0.0
        agg_b = db.query(func.avg(AcceptedMapping.s_final)).filter(
            AcceptedMapping.source_id == sid, AcceptedMapping.config == config_b, AcceptedMapping.forced_top1 == False
        ).scalar() or 0.0
        deltas.append({
            "source_id": sid,
            "avg_a": round(agg_a, 4),
            "avg_b": round(agg_b, 4),
            "delta": round(agg_b - agg_a, 4),
        })

    deltas.sort(key=lambda x: abs(x["delta"]), reverse=True)
    return {
        "prodi": prodi,
        "config_a": config_a,
        "config_b": config_b,
        "items": deltas,
        "summary": {
            "n_gain": sum(1 for x in deltas if x["delta"] > 0),
            "n_drop": sum(1 for x in deltas if x["delta"] < 0),
            "n_same": sum(1 for x in deltas if x["delta"] == 0),
        }
    }

@router.get("/stats")
def get_graph_stats(db: Session = Depends(get_db)):
    """Statistik graph untuk ditampilkan di homepage."""
    return {
        "total_nodes": db.query(KGNode).count(),
        "esco_skill_nodes": db.query(KGNode).filter(KGNode.node_type == "ESCO_SKILL").count(),
        "onet_nodes": db.query(KGNode).filter(KGNode.node_type == "ONET").count(),
        "skkni_nodes": db.query(KGNode).filter(KGNode.node_type == "SKKNI").count(),
        "total_edges": db.query(KGEdge).count(),
        "maps_to_edges": db.query(KGEdge).filter(KGEdge.edge_type == "MAPS_TO").count(),
    }


@router.get("/resolution-status")
def get_resolution_status(
    config: str = Query("v1.2"),
    db: Session = Depends(get_db),
):
    """Deteksi mapping yang target node-nya tidak berhasil di-resolve ke KG nodes."""
    mappings = db.query(AcceptedMapping).filter(AcceptedMapping.config == config).all()
    total = len(mappings)
    unresolved = []
    for m in mappings:
        node = _resolve_node(m.target_id, db, m.target_type)
        if node:
            continue
        unresolved.append(
            {
                "source_id": m.source_id,
                "target_id": m.target_id,
                "target_label": m.target_label,
                "target_type": m.target_type,
                "task": m.task,
                "forced_top1": bool(m.forced_top1),
            }
        )

    unresolved.sort(key=lambda x: (x["task"], x["source_id"], x["target_id"]))
    return {
        "config": config,
        "total_mappings": total,
        "unresolved_count": len(unresolved),
        "resolved_count": total - len(unresolved),
        "resolution_rate": round(((total - len(unresolved)) / total), 4) if total else 1.0,
        "samples": unresolved[:20],
    }
