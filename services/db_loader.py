# backend/services/db_loader.py
"""
Load output pipeline ke SQLite database lokal project (self-contained).
Jalankan: python -m services.db_loader

Compatible with:
- legacy layout: data/outputs/accepted_mappings/*.csv
- final snapshot layout: data/outputs/irkg_accepted_*.csv or external IRKG_RESULTS_DIR
"""

import json
import os
import re
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

# Add parent to path
sys.path.append(str(Path(__file__).parent.parent))
from database import engine, SessionLocal
from models import Base, CPLItem, CRIResult, AblationResult, AcceptedMapping, KGNode, KGEdge, CRIByRanah, DomainFilterResult

BASE_DIR = Path(__file__).resolve().parent.parent
PIPELINE_DIR = BASE_DIR / "pipeline"
DEFAULT_OUTPUTS_DIR = BASE_DIR / "data" / "outputs"
OUTPUTS_DIR = Path(os.getenv("IRKG_RESULTS_DIR", str(DEFAULT_OUTPUTS_DIR))).resolve()
DATA_DIR = BASE_DIR / "data" / "raw"

SKIP_V10 = os.getenv("IRKG_SKIP_V10", "1") != "0"
ACTIVE_CONFIGS = {"v0.9", "v1.1", "v1.2", "v1.3", "v1.4"} if SKIP_V10 else {
    "v0.9", "v1.0", "v1.1", "v1.2", "v1.3", "v1.4"
}

ESCO_URI_PREFIX = "http://data.europa.eu/esco/skill/"


def _accepted_dir() -> Path:
    legacy = OUTPUTS_DIR / "accepted_mappings"
    return legacy if legacy.exists() else OUTPUTS_DIR


def _accepted_files():
    return sorted(_accepted_dir().glob("irkg_accepted_*.csv"))


def _infer_task_config_from_name(name: str):
    m = re.match(r"irkg_accepted_(T\d[a-b]?)_(v\d\.\d)\.csv$", name)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def _target_type_for_task(task: str) -> str:
    if task in {"T1a", "T1b", "T4"}:
        return "ESCO"
    if task in {"T2a", "T2b", "T5"}:
        return "ONET"
    if task in {"T3a", "T3b"}:
        return "SKKNI"
    return "UNKNOWN"


def _normalize_esco_id(raw_id: str) -> str:
    raw = str(raw_id or "").strip()
    if not raw:
        return ""
    if raw.startswith(ESCO_URI_PREFIX):
        return raw
    return f"{ESCO_URI_PREFIX}{raw}"


def _load_esco_lookup() -> dict[str, str]:
    esco_df = pd.read_csv(DATA_DIR / "esco" / "esco_skills.csv", usecols=["conceptUri", "preferredLabel"])
    lookup = {}
    for _, row in esco_df.iterrows():
        full_id = str(row["conceptUri"])
        short_id = full_id.rsplit("/", 1)[-1]
        label = str(row["preferredLabel"])
        lookup[full_id] = label
        lookup[short_id] = label
    return lookup


def init_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("[DB] Tables recreated")


def _compute_cri_per_item_from_outputs(config_basis: str = "v1.2") -> pd.DataFrame:
    task_map = {
        "SI": {"ESCO": "T1a", "ONET": "T2a", "SKKNI": "T3a"},
        "TI": {"ESCO": "T1b", "ONET": "T2b", "SKKNI": "T3b"},
    }
    weights = {"ESCO": 0.40, "ONET": 0.35, "SKKNI": 0.25}

    cpl_si = pd.read_excel(DATA_DIR / "source_data" / "cpl_si.xlsx")
    cpl_si["source_id"] = "SI_" + cpl_si["id_cpl"].astype(str)
    cpl_ti = pd.read_excel(DATA_DIR / "source_data" / "cpl_ti.xlsx")
    cpl_ti["source_id"] = "TI_" + cpl_ti["id_cpl"].astype(str)
    cpl_meta = pd.concat(
        [
            cpl_si[["source_id", "ranah", "deskripsi_cpl"]].assign(prodi="SI"),
            cpl_ti[["source_id", "ranah", "deskripsi_cpl"]].assign(prodi="TI"),
        ],
        ignore_index=True,
    )

    task_frames = {}
    for task in ["T1a", "T1b", "T2a", "T2b", "T3a", "T3b"]:
        f = _accepted_dir() / f"irkg_accepted_{task}_{config_basis}.csv"
        if f.exists():
            task_frames[task] = pd.read_csv(f)
        else:
            task_frames[task] = pd.DataFrame(columns=["source_id", "target_id", "s_final", "forced_top1"])

    rows = []
    for _, row in cpl_meta.iterrows():
        prodi = row["prodi"]
        src = row["source_id"]
        r_vals = {}
        top_info = {}
        n_ok = {}

        for fw, task in task_map[prodi].items():
            df = task_frames[task]
            sub = df[df["source_id"] == src]
            ok = sub[~sub["forced_top1"]] if "forced_top1" in sub.columns else sub
            n_ok[fw] = int(len(ok))
            if len(ok) == 0:
                r_vals[fw] = 0.0
                top_info[fw] = ("", 0.0)
                continue
            r_vals[fw] = float(ok["s_final"].mean())
            best = ok.sort_values("s_final", ascending=False).iloc[0]
            top_info[fw] = (str(best.get("target_id", "")), float(best.get("s_final", 0.0)))

        cri = (
            weights["ESCO"] * r_vals["ESCO"]
            + weights["ONET"] * r_vals["ONET"]
            + weights["SKKNI"] * r_vals["SKKNI"]
        )
        zeros = sum(1 for v in r_vals.values() if v == 0.0)
        flag = "COMPLETE" if zeros == 0 else ("INCOMPLETE" if zeros == 3 else "PARTIAL")

        rows.append(
            {
                "source_id": src,
                "prodi": prodi,
                "ranah": row.get("ranah", ""),
                "r_esco": r_vals["ESCO"],
                "r_onet": r_vals["ONET"],
                "r_skkni": r_vals["SKKNI"],
                "cri_score": cri,
                "cri_flag": flag,
                "top_esco_label": top_info["ESCO"][0],
                "top_esco_score": top_info["ESCO"][1],
                "top_onet_label": top_info["ONET"][0],
                "top_onet_score": top_info["ONET"][1],
                "top_skkni_label": top_info["SKKNI"][0],
                "top_skkni_score": top_info["SKKNI"][1],
                "n_ok_esco": n_ok["ESCO"],
                "n_ok_onet": n_ok["ONET"],
                "n_ok_skkni": n_ok["SKKNI"],
                "config_basis": config_basis,
            }
        )

    return pd.DataFrame(rows)


def load_cri(db: Session):
    """Load CRI. Prefer item-level sheet; fallback to compute from accepted mappings."""
    cri_path = OUTPUTS_DIR / "cri_results.xlsx"
    if cri_path.exists():
        xls = pd.ExcelFile(cri_path)
        if "CRI_Per_CPL_Item" in xls.sheet_names:
            df = pd.read_excel(cri_path, sheet_name="CRI_Per_CPL_Item")
        else:
            df = _compute_cri_per_item_from_outputs(config_basis="v1.2")
    else:
        df = _compute_cri_per_item_from_outputs(config_basis="v1.2")

    for _, row in df.iterrows():
        item = CRIResult(
            source_id=row["source_id"],
            prodi=row["prodi"],
            ranah=row.get("ranah", ""),
            r_esco=row.get("r_esco", 0),
            r_onet=row.get("r_onet", 0),
            r_skkni=row.get("r_skkni", 0),
            cri_score=row.get("cri_score", 0),
            cri_flag=row.get("cri_flag", "INCOMPLETE"),
            top_esco_label=row.get("top_esco_label", ""),
            top_esco_score=row.get("top_esco_score", 0),
            top_onet_label=row.get("top_onet_label", ""),
            top_onet_score=row.get("top_onet_score", 0),
            top_skkni_label=row.get("top_skkni_label", ""),
            top_skkni_score=row.get("top_skkni_score", 0),
            n_ok_esco=int(row.get("n_ok_esco", 0)),
            n_ok_onet=int(row.get("n_ok_onet", 0)),
            n_ok_skkni=int(row.get("n_ok_skkni", 0)),
            config_basis=row.get("config_basis", "v1.2"),
        )
        db.merge(item)

    ranah_path = OUTPUTS_DIR / "irkg_coverage_by_ranah_summary.csv"
    if ranah_path.exists():
        ranah_df = pd.read_csv(ranah_path)
        for _, row in ranah_df.iterrows():
            db.merge(
                CRIByRanah(
                    ranah=row["ranah"],
                    n_items=int(row.get("n_items", 0)),
                    has_mapping_esco=row.get("has_mapping_esco", 0),
                    has_mapping_onet=row.get("has_mapping_onet", 0),
                    has_mapping_skkni=row.get("has_mapping_skkni", 0),
                    mean_sfinal_esco=row.get("mean_sfinal_esco", 0),
                    mean_sfinal_onet=row.get("mean_sfinal_onet", 0),
                    mean_sfinal_skkni=row.get("mean_sfinal_skkni", 0),
                )
            )
    else:
        ranah_df = (
            df.groupby("ranah", as_index=False)
            .agg(
                n_items=("source_id", "count"),
                has_mapping_esco=("r_esco", lambda s: (s > 0).mean()),
                has_mapping_onet=("r_onet", lambda s: (s > 0).mean()),
                has_mapping_skkni=("r_skkni", lambda s: (s > 0).mean()),
                mean_sfinal_esco=("r_esco", "mean"),
                mean_sfinal_onet=("r_onet", "mean"),
                mean_sfinal_skkni=("r_skkni", "mean"),
            )
            .fillna(0)
        )
        for _, row in ranah_df.iterrows():
            db.merge(
                CRIByRanah(
                    ranah=row["ranah"],
                    n_items=int(row["n_items"]),
                    has_mapping_esco=float(row["has_mapping_esco"]),
                    has_mapping_onet=float(row["has_mapping_onet"]),
                    has_mapping_skkni=float(row["has_mapping_skkni"]),
                    mean_sfinal_esco=float(row["mean_sfinal_esco"]),
                    mean_sfinal_onet=float(row["mean_sfinal_onet"]),
                    mean_sfinal_skkni=float(row["mean_sfinal_skkni"]),
                )
            )

    db.commit()
    print(f"[DB] CRI loaded: {len(df)} items")


def load_ablation(db: Session):
    """Load ablation from final workbook (preferred) with legacy fallback."""
    ablation_path = OUTPUTS_DIR / "irkg_ablation_final.xlsx"
    if not ablation_path.exists():
        ablation_path = OUTPUTS_DIR / "irkg_ablation_results.xlsx"

    for sheet, is_esco in [("ESCO_Target", True), ("NonESCO_Target", False)]:
        df = pd.read_excel(ablation_path, sheet_name=sheet)
        for _, row in df.iterrows():
            cfg = str(row.get("config", ""))
            if cfg not in ACTIVE_CONFIGS:
                continue
            item = AblationResult(
                task=row["task"],
                config=cfg,
                config_name=row.get("config_name", ""),
                esco_target=bool(row.get("esco_target", is_esco)),
                acceptance_rate=row.get("acceptance_rate", 0),
                source_coverage=row.get("source_coverage", 0),
                mean_final_score=row.get("mean_final_score", 0),
                forced_top1_ratio=row.get("forced_top1_ratio", 0),
                selection_objective=row.get("selection_objective", 0),
            )
            db.add(item)
    db.commit()
    print(f"[DB] Ablation loaded from: {ablation_path.name}")


def load_accepted_mappings(db: Session):
    """Load accepted mappings from either legacy or final snapshot layout."""
    total = 0
    chunk_size = 5000
    esco_lookup = _load_esco_lookup()
    for csv_file in _accepted_files():
        task_from_name, cfg_from_name = _infer_task_config_from_name(csv_file.name)
        if task_from_name in {"T4", "T5"}:
            continue
        if cfg_from_name and cfg_from_name not in ACTIVE_CONFIGS:
            continue

        df = pd.read_csv(csv_file)
        if len(df) == 0:
            continue

        if "task" not in df.columns:
            df["task"] = task_from_name or ""
        if "config" not in df.columns:
            df["config"] = cfg_from_name or ""
        if "target_type" not in df.columns:
            df["target_type"] = df["task"].map(_target_type_for_task).fillna("UNKNOWN")
        if "target_label" not in df.columns:
            df["target_label"] = df.get("target_id", "")
        if "source_text" not in df.columns:
            df["source_text"] = ""

        df = df.drop_duplicates(
            subset=["source_id", "target_id", "task", "config", "forced_top1"],
            keep="first",
        )

        records = []
        for _, row in df.iterrows():
            cfg = str(row.get("config", ""))
            if cfg and cfg not in ACTIVE_CONFIGS:
                continue

            target_type = str(row.get("target_type", ""))
            target_id = str(row.get("target_id", ""))
            target_label = str(row.get("target_label", ""))

            if target_type == "ESCO":
                target_id = _normalize_esco_id(target_id)
                if (not target_label) or (target_label == str(row.get("target_id", ""))):
                    target_label = esco_lookup.get(target_id, esco_lookup.get(target_id.rsplit("/", 1)[-1], target_label))

            records.append(
                AcceptedMapping(
                    source_id=str(row.get("source_id", "")),
                    source_text=str(row.get("source_text", "")),
                    target_id=target_id,
                    target_label=target_label,
                    target_type=target_type,
                    s_sem=float(row.get("s_sem", 0)),
                    s_gr=float(row.get("s_gr", 0)),
                    s_con=float(row.get("s_con", 1)),
                    s_final=float(row.get("s_final", 0)),
                    forced_top1=bool(row.get("forced_top1", False)),
                    task=str(row.get("task", "")),
                    config=cfg,
                )
            )
            if len(records) >= chunk_size:
                db.bulk_save_objects(records)
                db.commit()
                records = []

        if records:
            db.bulk_save_objects(records)
            db.commit()

        total += len(df)

    print(f"[DB] Accepted mappings loaded: {total} records")


def load_kg_nodes(db: Session):
    """Load ESCO skills + CPL items sebagai KG nodes"""
    esco_df = pd.read_csv(DATA_DIR / "esco" / "esco_skills.csv")
    esco_df["description"] = esco_df["description"].fillna("")
    for _, row in esco_df.iterrows():
        node = KGNode(
            id=row["conceptUri"],
            label=row["preferredLabel"],
            node_type="ESCO_SKILL",
            description=str(row["description"])[:500],
            extra=json.dumps({"skillType": row.get("skillType", "")})
        )
        db.merge(node)
    print(f"[DB] ESCO skills loaded: {len(esco_df)} nodes")

    onet_df = pd.read_csv(DATA_DIR / "source_data" / "onet_occupations.csv")
    for _, row in onet_df.iterrows():
        node = KGNode(
            id=row["soc_code"],
            label=row["title"],
            node_type="ONET",
            description=str(row.get("onet_text_enriched", ""))[:300],
            extra=json.dumps({"major_group": str(row.get("major_group_code", ""))})
        )
        db.merge(node)
    print(f"[DB] O*NET loaded: {len(onet_df)} nodes")

    skkni_df = pd.read_csv(DATA_DIR / "source_data" / "skkni_enriched.csv")
    for _, row in skkni_df.iterrows():
        node = KGNode(
            id=row["kode_unit"],
            label=row["judul_unit"],
            node_type="SKKNI",
            description=str(row.get("deskripsi_unit_clean", ""))[:300],
            extra=json.dumps({"sector": str(row.get("doc_sector", ""))})
        )
        db.merge(node)
    print(f"[DB] SKKNI loaded: {len(skkni_df)} nodes")

    cpl_df = pd.read_excel(DATA_DIR / "source_data" / "cpl_si.xlsx")
    for _, row in cpl_df.iterrows():
        db.merge(KGNode(
            id=f"SI_{row['id_cpl']}",
            label=f"SI_{row['id_cpl']}",
            node_type="CPL",
            description=str(row.get("deskripsi_cpl", ""))[:200],
            extra=json.dumps({"ranah": str(row.get("ranah", "")), "prodi": "SI"})
        ))

    cpl_ti_df = pd.read_excel(DATA_DIR / "source_data" / "cpl_ti.xlsx")
    for _, row in cpl_ti_df.iterrows():
        db.merge(KGNode(
            id=f"TI_{row['id_cpl']}",
            label=f"TI_{row['id_cpl']}",
            node_type="CPL",
            description=str(row.get("deskripsi_cpl", ""))[:200],
            extra=json.dumps({"ranah": str(row.get("ranah", "")), "prodi": "TI"})
        ))

    print(f"[DB] CPL nodes loaded: {len(cpl_df) + len(cpl_ti_df)}")
    db.commit()


def load_kg_edges(db: Session):
    """Load graph relations sebagai KG edges"""
    mappings = db.query(AcceptedMapping).filter(
        AcceptedMapping.config == "v1.2",
        AcceptedMapping.forced_top1 == False
    ).all()

    for m in mappings:
        db.add(KGEdge(
            source_id=m.source_id,
            target_id=m.target_id,
            edge_type="MAPS_TO",
            weight=m.s_final,
            config="v1.2"
        ))
    print(f"[DB] MAPS_TO edges loaded: {len(mappings)}")

    broader_df = pd.read_csv(DATA_DIR / "graph_relations" / "skill_broader_relations.csv")
    for _, row in broader_df.head(5000).iterrows():
        db.add(KGEdge(
            source_id=row["conceptUri"],
            target_id=row["broaderUri"],
            edge_type="BROADER",
            weight=1.0,
            config=None
        ))

    related_df = pd.read_csv(DATA_DIR / "graph_relations" / "skill_skill_relations.csv")
    for _, row in related_df.iterrows():
        db.add(KGEdge(
            source_id=row["originalSkillUri"],
            target_id=row["relatedSkillUri"],
            edge_type="RELATED",
            weight=1.0,
            config=None
        ))

    db.commit()
    print("[DB] Structural edges loaded")


DOMAIN_FILTER_CSV = OUTPUTS_DIR / "irkg_domain_filter.csv"


def load_domain_filter(db: Session):
    """
    Load domain filter results ke domain_filter_results.
    Jika CSV belum ada, jalankan stage00 secara inline terlebih dahulu.
    """
    if not DOMAIN_FILTER_CSV.exists():
        print("[DB] irkg_domain_filter.csv tidak ditemukan — menjalankan Stage 00...")
        try:
            if str(PIPELINE_DIR) not in sys.path:
                sys.path.insert(0, str(PIPELINE_DIR))
            from stage00_domain_filter import run_domain_filter
            run_domain_filter()
        except Exception as e:
            print(f"[DB] Stage 00 gagal: {e}")
            import traceback
            traceback.print_exc()
            return

    if not DOMAIN_FILTER_CSV.exists():
        print("[DB] irkg_domain_filter.csv masih tidak ditemukan, skip domain filter.")
        return

    df = pd.read_csv(DOMAIN_FILTER_CSV)
    if df.empty:
        print("[DB] irkg_domain_filter.csv kosong, skip.")
        return

    chunk_size = 5000
    records = []
    for _, row in df.iterrows():
        records.append(DomainFilterResult(
            prodi=str(row["prodi"]),
            node_id=str(row["node_id"]),
            s_con=float(row["s_con"]),
            domain_status=str(row["domain_status"]),
            config=str(row["config"]),
            sim_score=float(row["sim_score"]) if "sim_score" in df.columns else 0.0,
        ))
        if len(records) >= chunk_size:
            db.bulk_save_objects(records)
            db.commit()
            records = []
    if records:
        db.bulk_save_objects(records)
        db.commit()

    print(f"[DB] Domain filter loaded: {len(df)} rows ({df['prodi'].nunique()} prodi)")


def run_all():
    print(f"[DB] OUTPUTS_DIR = {OUTPUTS_DIR}")
    print(f"[DB] SKIP_V10 = {SKIP_V10}")
    init_db()
    db = SessionLocal()
    try:
        load_cri(db)
        load_ablation(db)
        load_accepted_mappings(db)
        load_kg_nodes(db)
        load_kg_edges(db)
        load_domain_filter(db)
        print(f"\n[DB] Semua data berhasil dimuat ke {BASE_DIR / 'data' / 'db' / 'irkg.db'}")
    except Exception as e:
        print(f"\n[DB] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    run_all()


