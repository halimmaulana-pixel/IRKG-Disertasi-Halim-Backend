# IR-KG Pipeline

Pipeline implementasi framework IR-KG (Information Retrieval + Knowledge Graph) untuk pemetaan kompetensi lintas-framework.

## Struktur

```
irkg-pipeline/
├── config.py              # Konfigurasi dan parameter
├── data_loader.py         # Data loading dengan bridge dictionary
├── stage01_preprocess.py  # TF-IDF vectorizer
├── stage02_candidates.py  # Top-k candidate generation
├── stage03_graph.py       # Graph cohesion score (S_gr)
├── stage04_scorer.py      # Hybrid scoring + acceptance gate
├── stage05_evaluator.py   # Metrics + ablation study
├── stage06_ecv.py         # External Consistency Validation
├── t10_cri.py             # CRI-KG computation
├── main.py                # Entry point
├── requirements.txt
└── README.md
```

## Usage

```bash
# Full pipeline dengan semua task dan config
python main.py --all

# Ablation study semua task
python main.py --ablation

# Single task testing
python main.py --task T1a --config v1.2

# Hanya CRI computation (setelah pipeline selesai)
python main.py --cri

# Hanya ECV
python main.py --ecv
```

## Output

```
outputs/
├── irkg_ablation_results.xlsx   # 2 sheet: ESCO_Target + NonESCO_Target
├── irkg_evidence_paths.jsonl    # Evidence per mapping
├── cri_results.xlsx             # 3 sheet: Per CPL, Per Prodi, Gap Analysis
├── ecv_results.csv              # External consistency metrics
├── irkg_summary.json            # Pipeline summary
└── accepted_mappings/           # 48 CSV (8 tasks × 6 configs)
    └── irkg_accepted_T1a_v1.2.csv
```

## Dataset

Dataset berada di folder `cri-kg/dataset/`:
- `source_data/`: CPL (SI, TI), SKKNI, O*NET
- `esco/`: ESCO skills, occupations, hierarchy
- `graph_relations/`: occ-skill, skill-skill, skill-broader relations
- `bridge/`: Bridge dictionary untuk cross-lingual
- `esco_onet_crosswalk_clean.csv`: Official crosswalk
