# CHANGELOG — irkg-pipeline-v1.1

## v1.1 — 2026-03-04

### Changed
- `config.py`: v1.0 tau strategy diubah dari "global_0.45" ke "quantile_50"
  → v1.0 tidak lagi collapse (100% forced)
- `config.py`: Tambah PIPELINE_VERSION dan PIPELINE_DATE

### Added
- `t10_cri.py`: Kolom diagnostik baru (n_ok_esco, n_ok_onet, n_ok_skkni,
  has_esco_forced, has_onet_forced, has_skkni_forced)
- `stage05_evaluator.py`: Fungsi analyze_coverage_by_ranah()
- Output baru: irkg_coverage_by_ranah_detail.csv
- Output baru: irkg_coverage_by_ranah_summary.csv
- `PROJECT_REPORT_v1.1.md`: Laporan update dengan perbandingan v1.0 vs v1.1

### Fixed
- Bug: Config v1.0 menghasilkan 100% forced_top1 karena tau=global_0.45
  terlalu tinggi relative terhadap distribusi S_final aktual

### Not Changed (intentional)
- CRI score yang rendah untuk CPL ranah Sikap DIPERTAHANKAN
  (ini temuan substantif, bukan bug)
- ECV consistency rate ~20% DIPERTAHANKAN
  (dalam rentang normal untuk 3-hop chain validation)
- Formula scoring, threshold, dan semua parameter utama TIDAK DIUBAH
  (perubahan parameter = eksperimen baru, bukan perbaikan)
- Bridge dictionary tidak ditambah untuk istilah soft skills/Sikap
  (temuannya memang valid: CPL Sikap sulit dipetakan ke framework teknis)

---

## v1.0 — 2026-03-04

### Initial Release
- Full IR-KG pipeline dengan 8 tasks dan 6 ablation configs
- TF-IDF + Graph Cohesion + Hybrid Scoring
- CRI-KG computation
- ECV (External Consistency Validation)
- Output: 48 CSV + Excel + JSONL

### Known Issues in v1.0
1. Config v1.0 collapse (100% forced) - FIXED in v1.1
2. CPL ranah Sikap coverage rendah - INTENTIONAL (temuan substantif)
3. ECV Chain 1 hanya 8 sources - INTENTIONAL (konsekuensi dari #2)
