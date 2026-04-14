"""
Cross-institution CPL test — INDUCTIVE approach.

Vectorizer difit HANYA dari target corpus (ESCO / O*NET / SKKNI).
CPL dari universitas manapun cukup di-transform() sebagai query.
Ini konsisten dengan prinsip: CPL adalah INPUT (query), bukan bagian training.

Universitas diuji: UMSU (baseline), ITK, UI, PENS, UGM
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "pipeline"))

import pandas as pd
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pipeline.data_loader import apply_bridge

OUTPUTS    = BACKEND / "data" / "outputs"
SOURCE_DIR = BACKEND / "data" / "raw" / "source_data"
ESCO_DIR   = BACKEND / "data" / "raw" / "esco"

# ─── 1. Load target corpora ───────────────────────────────────────────────

def load_esco():
    df = pd.read_csv(ESCO_DIR / "esco_skills.csv").dropna(subset=["preferredLabel"])
    desc = df["description"].fillna("") if "description" in df.columns else ""
    df["text"] = (df["preferredLabel"].fillna("") + " " + desc).str.strip()
    return df[["conceptUri", "preferredLabel", "text"]].rename(
        columns={"conceptUri": "id", "preferredLabel": "label"}).reset_index(drop=True)

def load_onet():
    df = pd.read_csv(SOURCE_DIR / "onet_occupations.csv")
    df["text"] = (df["title"].fillna("") + " " + df["onet_text_enriched"].fillna("")).str.strip()
    return df[["soc_code", "title", "text"]].rename(
        columns={"soc_code": "id", "title": "label"}).reset_index(drop=True)

def load_skkni():
    df = pd.read_csv(SOURCE_DIR / "skkni_enriched.csv")
    cols = df.columns.tolist()
    id_col    = cols[0]
    label_col = next((c for c in cols if "judul" in c.lower()), cols[1])
    desc_col  = next((c for c in cols if "enriched" in c.lower() or "deskripsi" in c.lower()), label_col)
    df["text"] = (df[label_col].fillna("") + " " + df[desc_col].fillna("")).str.strip()
    return df[[id_col, label_col, "text"]].rename(
        columns={id_col: "id", label_col: "label"}).reset_index(drop=True)

# ─── 2. Build inductive vectorizer (fit HANYA target corpus) ─────────────

def build_inductive_vectorizer(corpus_texts: list, lang: str = "en"):
    """Fit vectorizer hanya dari target corpus."""
    vec = TfidfVectorizer(
        max_features=15000,
        ngram_range=(1, 2),
        sublinear_tf=True,
        min_df=1,
        strip_accents="unicode",
        analyzer="word",
    )
    vec.fit(corpus_texts)
    print(f"  Inductive vectorizer ({lang}): {len(corpus_texts)} docs, vocab={len(vec.vocabulary_)}")
    return vec

# ─── 3. Top-k matching ────────────────────────────────────────────────────

def top_k(query_text: str, vec, matrix, corpus_df, k=5) -> list:
    """Transform query text, hitung cosine similarity, return top-k."""
    q_vec = vec.transform([query_text])
    sims  = cosine_similarity(q_vec, matrix).flatten()
    idx   = sims.argsort()[::-1][:k]
    return [
        {
            "target_id":    corpus_df.iloc[i]["id"],
            "target_label": corpus_df.iloc[i]["label"],
            "s_sem":        round(float(sims[i]), 4),
            "rank":         r + 1,
        }
        for r, i in enumerate(idx)
    ]

# ─── 4. Load CPL datasets ─────────────────────────────────────────────────

UNIVERSITIES = [
    ("UMSU_SI",  "cpl_si.xlsx",            "SI",  "id"),   # baseline original
    ("UMSU_TI",  "cpl_ti.xlsx",            "TI",  "id"),   # baseline original
    ("ITK",      "cpl_itk_informatika.xlsx", None, "id"),
    ("UI_SI",    "cpl_ui_si.xlsx",          None, "id"),
    ("PENS",     "cpl_pens_tekkom.xlsx",    None, "id"),
    ("UGM_TI",   "cpl_ugm_ti.xlsx",         None, "id"),
]

def load_cpl_df(filename, prodi_prefix):
    df = pd.read_excel(SOURCE_DIR / filename)
    if prodi_prefix:
        # CPL UMSU pakai kolom id_cpl → bridge apply
        df["source_id"] = prodi_prefix + "_" + df["id_cpl"]
        df["bridged"]   = df["deskripsi_cpl"].apply(apply_bridge)
    else:
        df["source_id"] = df["id_cpl"]
        df["bridged"]   = df["deskripsi_cpl"].apply(apply_bridge)
    return df[["source_id", "ranah", "deskripsi_cpl", "bridged"]]

# ─── MAIN ─────────────────────────────────────────────────────────────────

print("=" * 65)
print(" INDUCTIVE CPL TEST — vectorizer difit dari target corpus only")
print("=" * 65)

# Load corpora
print("\n[1] Loading target corpora...")
esco_df  = load_esco()
onet_df  = load_onet()
skkni_df = load_skkni()
print(f"    ESCO: {len(esco_df)} | O*NET: {len(onet_df)} | SKKNI: {len(skkni_df)}")

# Build inductive vectorizers
print("\n[2] Building inductive vectorizers (target corpus only)...")
vec_esco  = build_inductive_vectorizer(esco_df["text"].tolist(),  lang="EN-ESCO")
vec_onet  = build_inductive_vectorizer(onet_df["text"].tolist(),  lang="EN-ONET")
vec_skkni = build_inductive_vectorizer(skkni_df["text"].tolist(), lang="ID-SKKNI")

# Pre-compute target matrices
print("\n[3] Pre-computing target TF-IDF matrices...")
mat_esco  = vec_esco.transform(esco_df["text"].tolist())
mat_onet  = vec_onet.transform(onet_df["text"].tolist())
mat_skkni = vec_skkni.transform(skkni_df["text"].tolist())
print("    Done.")

TARGETS = [
    ("ESCO",  vec_esco,  mat_esco,  esco_df),
    ("ONET",  vec_onet,  mat_onet,  onet_df),
    ("SKKNI", vec_skkni, mat_skkni, skkni_df),
]

# Run queries
print("\n[4] Running CPL queries...\n")
all_results = []

for univ_code, filename, prodi_prefix, _ in UNIVERSITIES:
    df_cpl = load_cpl_df(filename, prodi_prefix)
    print(f"  -- {univ_code} ({len(df_cpl)} CPL) --")

    for _, row in df_cpl.iterrows():
        cpl_id      = row["source_id"]
        cpl_raw     = row["deskripsi_cpl"]
        cpl_bridged = row["bridged"]

        for fw_name, vec, mat, corpus in TARGETS:
            # Cross-lingual (ESCO/ONET): gunakan bridged text
            # Monolingual (SKKNI): gunakan raw Indonesian text
            query = cpl_raw if fw_name == "SKKNI" else cpl_bridged
            matches = top_k(query, vec, mat, corpus, k=5)
            top = matches[0]
            print(f"    {cpl_id:22s} | {fw_name:5s} | {top['target_label'][:45]:45s} s={top['s_sem']:.4f}")
            for m in matches:
                all_results.append({
                    "univ":             univ_code,
                    "cpl_id":           cpl_id,
                    "ranah":            row["ranah"],
                    "cpl_text":         cpl_raw[:100],
                    "framework":        fw_name,
                    "target_id":        m["target_id"],
                    "target_label":     m["target_label"],
                    "s_sem":            m["s_sem"],
                    "rank":             m["rank"],
                    "query_mode":       "raw" if fw_name == "SKKNI" else "bridged",
                })
    print()

# Save
out_df   = pd.DataFrame(all_results)
out_path = OUTPUTS / "external_cpl_inductive_results.xlsx"
out_df.to_excel(out_path, index=False)
print(f"\n[SAVED] {len(out_df)} rows -> {out_path}")

# ─── Summary ─────────────────────────────────────────────────────────────

print("\n" + "=" * 65)
print(" SUMMARY — Mean S_sem (top-1) per Universitas × Framework")
print("=" * 65)
top1 = out_df[out_df["rank"] == 1]
pivot = top1.groupby(["univ", "framework"])["s_sem"].mean().round(4).unstack()
# reorder columns
for col in ["ESCO", "ONET", "SKKNI"]:
    if col not in pivot.columns:
        pivot[col] = float("nan")
print(pivot[["ESCO", "ONET", "SKKNI"]].to_string())

print("\n" + "=" * 65)
print(" PERBANDINGAN per Ranah (mean s_sem top-1, semua universitas)")
print("=" * 65)
ranah_pivot = top1.groupby(["ranah", "framework"])["s_sem"].mean().round(4).unstack()
for col in ["ESCO", "ONET", "SKKNI"]:
    if col not in ranah_pivot.columns:
        ranah_pivot[col] = float("nan")
print(ranah_pivot[["ESCO", "ONET", "SKKNI"]].to_string())

print("\n[DONE]")
