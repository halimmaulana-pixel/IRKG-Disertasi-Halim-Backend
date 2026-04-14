# stage02_candidates.py
"""
Generate top-k candidates untuk setiap source item.
Output: dict {task_id: DataFrame} dengan kolom
  [source_id, target_id, s_sem, rank]
"""
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import linear_kernel
from config import TOP_K, BATCH_SIZE, TASK_DEFINITIONS, OUTPUT_DIR
from data_loader import load_cpl, load_skkni, load_esco_skills, load_onet


def get_source_target_data(task_id: str):
    """Load source dan target data untuk task tertentu."""
    task = TASK_DEFINITIONS[task_id]
    src_key = task["source"]
    tgt_key = task["target"]

    # Load source
    if src_key == "cpl_si":
        src_df = load_cpl("SI")
        src_texts = src_df["bridged_text"].tolist()
        src_ids = src_df["id"].tolist()
    elif src_key == "cpl_ti":
        src_df = load_cpl("TI")
        src_texts = src_df["bridged_text"].tolist()
        src_ids = src_df["id"].tolist()
    elif src_key == "skkni":
        src_df = load_skkni()
        if task_id in ["T3a", "T3b"]:
            src_texts = src_df["deskripsi_unit_clean"].tolist()
        else:
            src_texts = src_df["deskripsi_unit_enriched"].tolist()
        src_ids = src_df["id"].tolist()

    # Load target
    if tgt_key == "esco_skills":
        tgt_df = load_esco_skills()
        tgt_texts = tgt_df["skill_text"].tolist()
        tgt_ids = tgt_df["id"].tolist()
        tgt_labels = tgt_df["preferredLabel"].tolist()
        tgt_type = "ESCO"
    elif tgt_key == "onet":
        tgt_df = load_onet()
        tgt_texts = tgt_df["onet_text_enriched"].tolist()
        tgt_ids = tgt_df["id"].tolist()
        tgt_labels = tgt_df["title"].tolist()
        tgt_type = "ONET"
    elif tgt_key == "skkni":
        tgt_df = load_skkni()
        tgt_texts = tgt_df["deskripsi_unit_clean"].tolist()
        tgt_ids = tgt_df["id"].tolist()
        tgt_labels = tgt_df["judul_unit"].tolist()
        tgt_type = "SKKNI"

    return src_ids, src_texts, tgt_ids, tgt_texts, tgt_labels, tgt_type


def generate_candidates(task_id: str, vectorizer) -> pd.DataFrame:
    """
    Generate top-k candidates menggunakan TF-IDF cosine similarity.
    Menggunakan batch processing untuk efisiensi memory.
    Returns DataFrame: [source_id, target_id, target_label, target_type, s_sem, rank]
    """
    src_ids, src_texts, tgt_ids, tgt_texts, tgt_labels, tgt_type = \
        get_source_target_data(task_id)

    n_src = len(src_ids)
    n_tgt = len(tgt_ids)
    print(f"[{task_id}] {n_src} sources × {n_tgt} targets = {n_src*n_tgt:,} comparisons")

    # Transform target sekali (sparse matrix)
    tgt_matrix = vectorizer.transform(tgt_texts)  # sparse (n_tgt × vocab)
    tgt_ids_arr = np.array(tgt_ids)
    tgt_labels_arr = np.array(tgt_labels)

    all_results = []

    # Batch process sources
    for batch_start in range(0, n_src, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, n_src)
        batch_texts = src_texts[batch_start:batch_end]
        batch_ids = src_ids[batch_start:batch_end]

        src_matrix = vectorizer.transform(batch_texts)  # sparse (batch × vocab)
        # Dense similarity matrix hanya untuk batch kecil
        sims = linear_kernel(src_matrix, tgt_matrix)  # (batch × n_tgt)

        for i, src_id in enumerate(batch_ids):
            sim_row = sims[i]
            # Ambil top-k tanpa sort penuh (argpartition lebih cepat)
            if len(sim_row) <= TOP_K:
                top_k_idx = np.arange(len(sim_row))
            else:
                top_k_idx = np.argpartition(sim_row, -TOP_K)[-TOP_K:]

            # Sort top-k descending
            top_k_idx = top_k_idx[np.argsort(sim_row[top_k_idx])[::-1]]

            for rank, idx in enumerate(top_k_idx):
                score = float(sim_row[idx])
                if score > 0:  # skip zero similarity
                    all_results.append({
                        "source_id": src_id,
                        "target_id": tgt_ids_arr[idx],
                        "target_label": tgt_labels_arr[idx],
                        "target_type": tgt_type,
                        "s_sem": round(score, 6),
                        "rank": rank + 1
                    })

        if batch_start % 200 == 0 or batch_end >= n_src:
            print(f"  [{task_id}] Progress: {batch_end}/{n_src}")

    df = pd.DataFrame(all_results)
    print(f"[{task_id}] Candidates generated: {len(df):,} pairs")
    return df


def run_all_candidate_generation(vectorizers: dict) -> dict:
    """Jalankan candidate generation untuk semua 8 tasks."""
    all_candidates = {}
    for task_id in TASK_DEFINITIONS:
        print(f"\n=== Generating candidates: {task_id} ===")
        candidates = generate_candidates(task_id, vectorizers[task_id])
        all_candidates[task_id] = candidates
    return all_candidates


if __name__ == "__main__":
    from stage01_preprocess import build_all_vectorizers
    vecs = build_all_vectorizers()
    run_all_candidate_generation(vecs)
