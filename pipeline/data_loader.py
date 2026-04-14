# data_loader.py

import pandas as pd
import sys
import re
from pathlib import Path
from config import PATHS


def apply_bridge(text: str) -> str:
    """
    Apply two-tier cross-lingual bridge to Indonesian text.
    Tier 1: shared IT terms remain unchanged
    Tier 2: apply lexical bridge dictionary
    Returns English-friendly text for TF-IDF vectorization.
    """
    if not isinstance(text, str):
        return ""
    
    # Import bridge dict
    sys.path.insert(0, str(PATHS["bridge"].parent))
    from bridge_dict import BRIDGE_DICT, SHARED_IT_TERMS
    
    text_lower = text.lower()
    # Apply Tier 2: sorted by length (longest first to avoid partial replacement)
    for id_term, en_term in sorted(BRIDGE_DICT.items(), key=lambda x: -len(x[0])):
        # Use word boundary-aware replacement
        pattern = r'(?<![a-zA-Z0-9])' + re.escape(id_term) + r'(?![a-zA-Z0-9])'
        text_lower = re.sub(pattern, en_term, text_lower)
    return text_lower


def load_cpl(prodi: str) -> pd.DataFrame:
    """
    Load CPL dataset.
    prodi: 'SI' atau 'TI'
    Returns DataFrame dengan kolom:
      - id: 'SI_PLO-1' dst
      - deskripsi_cpl: teks asli (Bahasa Indonesia)
      - bridged_text: setelah apply_bridge
      - ranah: metadata
      - prodi: 'SI' atau 'TI'
    """
    path = PATHS[f"cpl_{prodi.lower()}"]
    df = pd.read_excel(path)
    # Kolom aktual: id_cpl, ranah, deskripsi_cpl, mata_kuliah_terkait, level_kkni
    df["id"] = prodi + "_" + df["id_cpl"]
    df["bridged_text"] = df["deskripsi_cpl"].apply(apply_bridge)
    df["prodi"] = prodi
    return df[["id", "deskripsi_cpl", "bridged_text", "ranah", "prodi"]]


def load_skkni() -> pd.DataFrame:
    """
    Load SKKNI dataset.
    Returns DataFrame dengan kolom:
      - id: kode_unit (J.62DPM00.002.1 dst)
      - judul_unit: metadata
      - deskripsi_unit_clean: untuk T3 (monolingual ID->ID)
      - deskripsi_unit_enriched: untuk T4/T5 (cross-lingual)
      - doc_sector: metadata
    """
    df = pd.read_csv(PATHS["skkni"])
    # Kolom aktual: kode_unit, judul_unit, deskripsi_unit_clean,
    #               deskripsi_unit_enriched, doc_sector
    df = df.rename(columns={"kode_unit": "id"})
    return df[["id", "judul_unit", "deskripsi_unit_clean",
               "deskripsi_unit_enriched", "doc_sector"]]


def load_esco_skills() -> pd.DataFrame:
    """
    Load ESCO Skills.
    Returns DataFrame dengan kolom:
      - id: conceptUri
      - preferredLabel: label singkat
      - skill_text: preferredLabel + " " + description (untuk TF-IDF)
      - skillType: metadata
    """
    df = pd.read_csv(PATHS["esco_skills"])
    # Kolom aktual: conceptUri, preferredLabel, description, skillType
    df = df.rename(columns={"conceptUri": "id"})
    df["description"] = df["description"].fillna("")
    df["skill_text"] = df["preferredLabel"] + " " + df["description"]
    return df[["id", "preferredLabel", "skill_text", "skillType"]]


def load_esco_occupations() -> pd.DataFrame:
    """Load ESCO Occupations — digunakan untuk ECV lookup."""
    df = pd.read_csv(PATHS["esco_occ"])
    df = df.rename(columns={"conceptUri": "id"})
    return df[["id", "preferredLabel", "code"]]


def load_onet() -> pd.DataFrame:
    """
    Load O*NET occupations.
    Returns DataFrame dengan kolom:
      - id: soc_code
      - title: nama occupation
      - onet_text_enriched: teks TF-IDF
      - major_group_code: metadata
    """
    df = pd.read_csv(PATHS["onet"])
    # Kolom aktual: soc_code, title, major_group_code, onet_text_enriched
    df = df.rename(columns={"soc_code": "id"})
    return df[["id", "title", "onet_text_enriched", "major_group_code"]]


def load_graph_relations() -> dict:
    """
    Load semua graph relations untuk S_gr computation.
    Returns dict:
      - 'occ_skill': DataFrame occupationUri -> skillUri
      - 'skill_skill': DataFrame originalSkillUri -> relatedSkillUri
      - 'skill_broader': DataFrame conceptUri -> broaderUri
    """
    occ_skill = pd.read_csv(PATHS["occ_skill"])
    skill_skill = pd.read_csv(PATHS["skill_skill"])
    skill_broader = pd.read_csv(PATHS["skill_broader"])
    return {
        "occ_skill": occ_skill,
        "skill_skill": skill_skill,
        "skill_broader": skill_broader
    }


def load_crosswalk() -> pd.DataFrame:
    """
    Load ESCO-O*NET crosswalk.
    Kolom aktual: onet_code, onet_title, onet_description, esco_uri, esco_title, esco_description, match_type
    Normalize ke:
      - esco_occ_uri: ESCO occupation URI
      - onet_soc_code: soc_code O*NET
      - relation_type: exactMatch/closeMatch/broadMatch/narrowMatch
    """
    df = pd.read_csv(PATHS["crosswalk"])
    
    # Rename ke nama standar internal pipeline
    df = df.rename(columns={
        "onet_code":  "onet_soc_code",   # "11-1011.00"
        "esco_uri":   "esco_occ_uri",    # "http://data.europa.eu/esco/occupation/..."
        "match_type": "relation_type",   # "exactMatch" / "closeMatch" / dll
    })

    print(f"[Crosswalk] Rows: {len(df)}")
    print(f"[Crosswalk] Relation types: {df['relation_type'].value_counts().to_dict()}")
    print(f"[Crosswalk] O*NET codes unique: {df['onet_soc_code'].nunique()}")
    print(f"[Crosswalk] ESCO occ unique: {df['esco_occ_uri'].nunique()}")

    return df[["onet_soc_code", "onet_title", "esco_occ_uri",
               "esco_title", "relation_type"]]
