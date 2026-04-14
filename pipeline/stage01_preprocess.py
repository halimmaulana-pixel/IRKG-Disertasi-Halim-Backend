# stage01_preprocess.py
"""
Membangun TF-IDF vectorizer per task.
Setiap task punya corpus yang berbeda (source + target teks digabung).
"""
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from config import TFIDF_MAX_FEATURES, TFIDF_NGRAM_RANGE, OUTPUT_DIR
from data_loader import (load_cpl, load_skkni, load_esco_skills,
                          load_onet, load_graph_relations)


def build_vectorizer(corpus: list, task_id: str) -> TfidfVectorizer:
    """Fit TF-IDF vectorizer pada corpus gabungan source+target."""
    vec = TfidfVectorizer(
        max_features=TFIDF_MAX_FEATURES,
        ngram_range=TFIDF_NGRAM_RANGE,
        sublinear_tf=True,
        min_df=1,
        strip_accents="unicode",
        analyzer="word"
    )
    vec.fit(corpus)
    # Simpan vectorizer untuk reproducibility
    out_path = OUTPUT_DIR / f"vectorizer_{task_id}.pkl"
    with open(out_path, "wb") as f:
        pickle.dump(vec, f)
    print(f"[{task_id}] Vectorizer fitted: {len(corpus)} docs, vocab={len(vec.vocabulary_)}")
    return vec


def build_all_vectorizers() -> dict:
    """
    Bangun vectorizer untuk semua task.
    PENTING: setiap task menggunakan corpus source+target-nya sendiri.
    Returns dict {task_id: vectorizer}
    """
    # Load semua data
    cpl_si = load_cpl("SI")
    cpl_ti = load_cpl("TI")
    skkni = load_skkni()
    esco = load_esco_skills()
    onet = load_onet()

    # Teks per dataset
    texts = {
        "cpl_si_bridged": cpl_si["bridged_text"].tolist(),
        "cpl_ti_bridged": cpl_ti["bridged_text"].tolist(),
        "cpl_si_raw":     cpl_si["deskripsi_cpl"].tolist(),
        "cpl_ti_raw":     cpl_ti["deskripsi_cpl"].tolist(),
        "skkni_clean":    skkni["deskripsi_unit_clean"].tolist(),
        "skkni_enriched": skkni["deskripsi_unit_enriched"].tolist(),
        "esco_skill":     esco["skill_text"].tolist(),
        "onet_enriched":  onet["onet_text_enriched"].tolist(),
    }

    # Build vectorizer per task dengan corpus gabungan
    task_vectorizers = {}
    task_corpora = {
        # Cross-lingual tasks: source (bridged/enriched) + target EN
        "T1a": ("cpl_si_bridged", "esco_skill"),
        "T1b": ("cpl_ti_bridged", "esco_skill"),
        "T2a": ("cpl_si_bridged", "onet_enriched"),
        "T2b": ("cpl_ti_bridged", "onet_enriched"),
        # Monolingual tasks: source + target (keduanya Indonesia)
        "T3a": ("cpl_si_raw",     "skkni_clean"),
        "T3b": ("cpl_ti_raw",     "skkni_clean"),
        # Cross-lingual large tasks
        "T4":  ("skkni_enriched", "esco_skill"),
        "T5":  ("skkni_enriched", "onet_enriched"),
    }

    for task_id, (src_key, tgt_key) in task_corpora.items():
        corpus = texts[src_key] + texts[tgt_key]
        vec = build_vectorizer(corpus, task_id)
        task_vectorizers[task_id] = vec

    return task_vectorizers


def load_all_vectorizers() -> dict:
    """Load vectorizer dari pkl yang sudah ada (skip re-fitting)."""
    import os
    task_ids = ["T1a", "T1b", "T2a", "T2b", "T3a", "T3b", "T4", "T5"]
    vectorizers = {}
    for task_id in task_ids:
        path = OUTPUT_DIR / f"vectorizer_{task_id}.pkl"
        if path.exists():
            with open(path, "rb") as f:
                vectorizers[task_id] = pickle.load(f)
            print(f"[{task_id}] Vectorizer loaded from pkl: vocab={len(vectorizers[task_id].vocabulary_)}")
        else:
            print(f"[{task_id}] WARNING: vectorizer_{task_id}.pkl tidak ditemukan, skip")
    return vectorizers


if __name__ == "__main__":
    build_all_vectorizers()
    print("[stage01] Semua vectorizer selesai.")
