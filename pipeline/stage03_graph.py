# stage03_graph.py
"""
Menghitung S_gr (Graph Cohesion Score) untuk setiap candidate pair.

S_gr untuk task ESCO-target (T1a, T1b, T4):
  - Untuk setiap source item, ambil top-k ESCO candidates-nya
  - Bangun induced subgraph dari top-k candidates di ESCO relations
  - S_gr(candidate) = jumlah neighbors candidate yang juga ada di top-k / (k-1)

S_gr untuk NON-ESCO tasks (T2, T3, T5):
  - S_gr = 0 untuk semua -> renormalize alpha/gamma saat scoring
"""
import pandas as pd
import numpy as np
from collections import defaultdict
from config import TASK_DEFINITIONS
from data_loader import load_graph_relations


def build_esco_adjacency(graph_relations: dict) -> dict:
    """
    Bangun adjacency list untuk ESCO graph.
    Menggabungkan: skill_skill + skill_broader relations.
    Returns: {skill_uri: set(related_skill_uris)}
    """
    adj = defaultdict(set)

    # Skill-skill relations
    ss = graph_relations["skill_skill"]
    for _, row in ss.iterrows():
        u = row["originalSkillUri"]
        v = row["relatedSkillUri"]
        adj[u].add(v)
        adj[v].add(u)  # undirected

    # Skill-broader relations (hierarki)
    sb = graph_relations["skill_broader"]
    for _, row in sb.iterrows():
        u = row["conceptUri"]
        v = row["broaderUri"]
        adj[u].add(v)
        adj[v].add(u)

    print(f"[graph] Adjacency built: {len(adj)} nodes, "
          f"{sum(len(v) for v in adj.values())//2} edges")
    return dict(adj)


def compute_sgr_for_task(candidates_df: pd.DataFrame,
                          adj: dict, task_id: str) -> pd.DataFrame:
    """
    Hitung S_gr untuk satu task.
    Hanya relevan untuk ESCO-target tasks (T1a, T1b, T4).
    Untuk non-ESCO tasks, langsung return dengan s_gr = 0.0
    """
    is_esco_target = TASK_DEFINITIONS[task_id]["esco_target"]

    if not is_esco_target:
        candidates_df["s_gr"] = 0.0
        return candidates_df

    results = []
    for src_id, group in candidates_df.groupby("source_id"):
        top_k_target_ids = set(group["target_id"].tolist())

        for _, row in group.iterrows():
            tgt_uri = row["target_id"]
            # Neighbors of this candidate in ESCO graph
            neighbors = adj.get(tgt_uri, set())
            # How many neighbors are also in the top-k set?
            cohesion = len(neighbors & top_k_target_ids)
            # Normalize by (k-1) to get [0,1]
            k = len(top_k_target_ids)
            s_gr = cohesion / (k - 1) if k > 1 else 0.0
            row_dict = row.to_dict()
            row_dict["s_gr"] = round(s_gr, 6)
            results.append(row_dict)

    return pd.DataFrame(results)


def compute_sgr_all_tasks(all_candidates: dict) -> dict:
    """Hitung S_gr untuk semua tasks."""
    print("[stage03] Loading graph relations...")
    graph_relations = load_graph_relations()
    adj = build_esco_adjacency(graph_relations)

    all_with_sgr = {}
    for task_id, candidates in all_candidates.items():
        print(f"[stage03] Computing S_gr for {task_id}...")
        df = compute_sgr_for_task(candidates.copy(), adj, task_id)
        all_with_sgr[task_id] = df
        sgr_mean = df["s_gr"].mean()
        print(f"  -> S_gr mean: {sgr_mean:.4f}")

    return all_with_sgr
