# stage06_ecv.py
"""
External Consistency Validation menggunakan ESCO-O*NET Official Crosswalk.

Chain 1 (CPL-based):
  CPL -> T1 (ESCO skills accepted) -> occ-skill lookup (top-3 ESCO occupations)
  -> crosswalk lookup -> expected O*NET E(cᵢ)
  -> compare dengan T2 accepted O*NET A(cᵢ)
  Konsisten jika A(cᵢ) ∩ E(cᵢ) ≠ ∅

Chain 2 (SKKNI-based):
  SKKNI -> T4 (ESCO skills accepted) -> occ-skill lookup (top-5 ESCO occupations)
  -> crosswalk lookup -> expected O*NET E(sᵢ)
  -> compare dengan T5 accepted O*NET A(sᵢ)

5 Metrik per chain:
  1. exact_consistency_rate (exactMatch only)
  2. relaxed_consistency_rate (semua tipe relasi)
  3. top1_consistency_rate
  4. at5_consistency_rate
  5. relation_type_distribution
"""
import pandas as pd
from collections import defaultdict
from config import OUTPUT_DIR, CRI_BASIS_CONFIG
from data_loader import load_crosswalk, load_graph_relations, load_esco_occupations


def build_occ_skill_index(graph_relations: dict) -> dict:
    """
    Build index: skill_uri -> set(occupation_uri)
    
    Arah lookup yang benar untuk ECV:
      - Kita punya: accepted ESCO skill URIs
      - Kita butuh: ESCO occupation URIs yang terkait
      - Jadi: skill -> occupation (bukan sebaliknya)

    Dari occ_skill_relations.csv:
      Kolom: occupationUri, relationType, skillType, skillUri
      -> Build: skillUri -> set(occupationUri)
    """
    occ_skill = graph_relations["occ_skill"]

    # Konfirmasi kolom (dari audit: occupationUri, relationType, skillType, skillUri)
    required_cols = {"occupationUri", "skillUri"}
    actual_cols = set(occ_skill.columns)
    if not required_cols.issubset(actual_cols):
        raise ValueError(
            f"occ_skill_relations.csv kolom tidak sesuai. "
            f"Expected: {required_cols}, Got: {actual_cols}"
        )

    skill_to_occ = defaultdict(set)
    for _, row in occ_skill.iterrows():
        skill_to_occ[row["skillUri"]].add(row["occupationUri"])

    print(f"[OccSkill Index] {len(skill_to_occ)} skill URIs -> occupations")
    print(f"[OccSkill Index] Total relations: {len(occ_skill)}")
    return dict(skill_to_occ)


def build_crosswalk_index(crosswalk_df: pd.DataFrame) -> dict:
    """
    Build index untuk lookup ECV:
      esco_occ_uri -> {onet_soc_code: relation_type}

    Contoh hasil:
      {
        "http://data.europa.eu/esco/occupation/5c5b153e...": {
          "11-1011.00": "closeMatch",
          "11-1021.00": "broadMatch",
          ...
        },
        ...
      }

    Digunakan di ECV chain:
      Step 1: accepted ESCO skills -> occ_skill lookup -> set of ESCO occ URIs
      Step 2: ESCO occ URIs -> crosswalk_index lookup -> expected O*NET soc_codes
      Step 3: compare expected vs actual (T2/T5 accepted O*NET)
    """
    xwalk_index = defaultdict(dict)

    for _, row in crosswalk_df.iterrows():
        esco_occ = row["esco_occ_uri"]
        onet_code = row["onet_soc_code"]
        rel_type = row["relation_type"]
        xwalk_index[esco_occ][onet_code] = rel_type

    print(f"[Crosswalk Index] {len(xwalk_index)} ESCO occupations terindeks")
    return dict(xwalk_index)


def run_chain(chain_id: int, source_task: str, bridge_task: str,
              all_results: dict, occ_skill_idx: dict,
              xwalk_idx: dict, top_n_occ: int = 3) -> dict:
    """
    Jalankan satu ECV chain.
    chain_id: 1 atau 2
    source_task: task yang menghasilkan ESCO mappings (T1a atau T4)
    bridge_task: task yang menghasilkan O*NET mappings (T2a atau T5)
    """
    basis_results = all_results[CRI_BASIS_CONFIG]
    esco_mappings = basis_results.get(source_task, pd.DataFrame())
    onet_mappings = basis_results.get(bridge_task, pd.DataFrame())

    if len(esco_mappings) == 0 or len(onet_mappings) == 0:
        print(f"[ECV Chain {chain_id}] Tidak ada data untuk {source_task} atau {bridge_task}")
        return {}

    metrics = {
        "chain": chain_id,
        "source_task": source_task,
        "bridge_task": bridge_task,
        "n_sources": 0,
        "exact_consistency": 0,
        "relaxed_consistency": 0,
        "top1_consistency": 0,
        "at5_consistency": 0,
        "relation_types": defaultdict(int)
    }

    source_ids = esco_mappings["source_id"].unique()
    metrics["n_sources"] = len(source_ids)

    for src_id in source_ids:
        # A(src): O*NET yang diterima dari bridge task
        a_onet = set(onet_mappings[
            (onet_mappings["source_id"] == src_id) &
            (~onet_mappings["forced_top1"])
        ]["target_id"].tolist())

        # ESCO skills accepted untuk source ini
        esco_skills = esco_mappings[
            (esco_mappings["source_id"] == src_id) &
            (~esco_mappings["forced_top1"])
        ]["target_id"].tolist()

        # Lookup: skills -> occupations -> crosswalk
        occ_counts = defaultdict(float)
        for skill_uri in esco_skills:
            for occ_uri in occ_skill_idx.get(skill_uri, set()):
                occ_counts[occ_uri] += 1

        # Top-N occupations
        top_occs = sorted(occ_counts, key=lambda x: -occ_counts[x])[:top_n_occ]

        # E(src): expected O*NET via crosswalk
        e_exact = set()
        e_any = set()
        for occ_uri in top_occs:
            for onet_code, rel_type in xwalk_idx.get(occ_uri, {}).items():
                e_any.add(onet_code)
                metrics["relation_types"][rel_type] += 1
                if rel_type == "exactMatch":
                    e_exact.add(onet_code)

        # Check consistency
        if len(a_onet) > 0 and len(e_any) > 0:
            if a_onet & e_exact:
                metrics["exact_consistency"] += 1
            if a_onet & e_any:
                metrics["relaxed_consistency"] += 1

        # Top-1 consistency
        top1_onet = onet_mappings[
            (onet_mappings["source_id"] == src_id)
        ].sort_values("s_final", ascending=False).head(1)
        if len(top1_onet) > 0:
            top1_id = top1_onet.iloc[0]["target_id"]
            if top1_id in e_any:
                metrics["top1_consistency"] += 1

        # @5 consistency
        top5_onet = set(onet_mappings[
            (onet_mappings["source_id"] == src_id)
        ].sort_values("s_final", ascending=False).head(5)["target_id"].tolist())
        if top5_onet & e_any:
            metrics["at5_consistency"] += 1

    n = metrics["n_sources"]
    if n > 0:
        metrics["exact_consistency_rate"] = round(metrics["exact_consistency"] / n, 4)
        metrics["relaxed_consistency_rate"] = round(metrics["relaxed_consistency"] / n, 4)
        metrics["top1_consistency_rate"] = round(metrics["top1_consistency"] / n, 4)
        metrics["at5_consistency_rate"] = round(metrics["at5_consistency"] / n, 4)

    return metrics


def run_ecv(all_results: dict):
    """Jalankan ECV Chain 1 dan Chain 2."""
    graph_relations = load_graph_relations()
    crosswalk_df = load_crosswalk()

    occ_skill_idx = build_occ_skill_index(graph_relations)
    xwalk_idx = build_crosswalk_index(crosswalk_df)

    # Chain 1: CPL-SI based
    chain1 = run_chain(1, "T1a", "T2a", all_results, occ_skill_idx, xwalk_idx, top_n_occ=3)
    # Chain 2: SKKNI based
    chain2 = run_chain(2, "T4", "T5", all_results, occ_skill_idx, xwalk_idx, top_n_occ=5)

    # Simpan hasil
    results_df = pd.DataFrame([
        {"chain": 1, "metric": k, "value": v}
        for k, v in chain1.items() if isinstance(v, (int, float))
    ] + [
        {"chain": 2, "metric": k, "value": v}
        for k, v in chain2.items() if isinstance(v, (int, float))
    ])

    out_path = OUTPUT_DIR / "ecv_results.csv"
    results_df.to_csv(out_path, index=False)

    print("\n[ECV] Chain 1 (CPL-based):")
    for k in ["exact_consistency_rate","relaxed_consistency_rate",
              "top1_consistency_rate","at5_consistency_rate"]:
        print(f"  {k}: {chain1.get(k, 'N/A')}")

    print("\n[ECV] Chain 2 (SKKNI-based):")
    for k in ["exact_consistency_rate","relaxed_consistency_rate",
              "top1_consistency_rate","at5_consistency_rate"]:
        print(f"  {k}: {chain2.get(k, 'N/A')}")

    return chain1, chain2
