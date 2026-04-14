# main.py - Pipeline IR-KG v1.1
"""
Entry point utama pipeline IR-KG.
Usage:
  python main.py --ablation              # Full ablation study (semua task, semua config)
  python main.py --task T1a              # Single task, all configs
  python main.py --task T1a --config v1.2  # Single task, single config
  python main.py --cri                   # Hanya CRI (butuh ablation sudah selesai)
  python main.py --ecv                   # Hanya ECV
  python main.py --all                   # Pipeline + CRI + ECV
"""
import argparse
import time
import json
from config import OUTPUT_DIR, ABLATION_CONFIGS, TASK_DEFINITIONS
import stage00_domain_filter as s00
import stage01_preprocess as s01
import stage02_candidates as s02
import stage03_graph as s03
import stage04_scorer as s04
import stage05_evaluator as s05
import stage06_ecv as s06
import t10_cri


def run_pipeline(tasks=None, configs=None):
    """Jalankan pipeline utama."""
    start = time.time()

    print("=" * 60)
    print("IR-KG PIPELINE — Halim Maulana, USU")
    print("=" * 60)

    # Stage 0: Domain filter pre-computation
    print("\n[Stage 00] Running domain filter pre-computation...")
    s00.run_domain_filter()

    # Stage 1: Build vectorizers
    print("\n[Stage 01] Building TF-IDF vectorizers...")
    vectorizers = s01.build_all_vectorizers()

    # Stage 2: Generate candidates
    print("\n[Stage 02] Generating top-k candidates...")
    all_candidates = s02.run_all_candidate_generation(vectorizers)

    # Filter tasks if specified
    if tasks:
        all_candidates = {t: d for t, d in all_candidates.items() if t in tasks}

    # Stage 3: Compute S_gr
    print("\n[Stage 03] Computing S_gr (graph cohesion scores)...")
    candidates_with_sgr = s03.compute_sgr_all_tasks(all_candidates)

    # Stage 4: Scoring + acceptance gate
    print("\n[Stage 04] Hybrid scoring + acceptance gate...")
    configs_to_run = configs or list(ABLATION_CONFIGS.keys())

    all_results = {}
    for cfg_id in configs_to_run:
        print(f"\n  Config: {cfg_id}")
        all_results[cfg_id] = s04.run_scorer_for_config(candidates_with_sgr, cfg_id)

    # Stage 5: Evaluation
    print("\n[Stage 05] Computing metrics + building ablation table...")
    ablation_df = s05.run_evaluation(all_results, all_candidates)
    
    # v1.1: Coverage analysis by ranah
    print("\n[Stage 05b] Analyzing coverage by CPL ranah...")
    s05.analyze_coverage_by_ranah(all_results, basis_config="v1.2")

    elapsed = time.time() - start
    print(f"\n[Pipeline] Selesai dalam {elapsed:.1f}s")

    # Simpan summary
    summary = {
        "version": "v1.1",
        "date": "2026-03-04",
        "tasks_run": list(all_candidates.keys()),
        "configs_run": configs_to_run,
        "elapsed_seconds": round(elapsed, 1),
        "n_accepted_total": sum(
            len(df) for cfg in all_results.values()
            for df in cfg.values()
        )
    }
    with open(OUTPUT_DIR / "irkg_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    return all_results, all_candidates


def main():
    parser = argparse.ArgumentParser(description="IR-KG Pipeline")
    parser.add_argument("--ablation", action="store_true",
                        help="Full ablation: semua task, semua config")
    parser.add_argument("--task", type=str, help="Single task (T1a, T1b, ...)")
    parser.add_argument("--config", type=str, help="Single config (v0.9, v1.2, ...)")
    parser.add_argument("--cri", action="store_true", help="Run CRI computation")
    parser.add_argument("--ecv", action="store_true", help="Run ECV validation")
    parser.add_argument("--all", action="store_true", help="Pipeline + CRI + ECV")
    args = parser.parse_args()

    tasks = [args.task] if args.task else None
    configs = [args.config] if args.config else None

    if args.all or args.ablation or args.task:
        all_results, all_candidates = run_pipeline(tasks, configs)

        if args.all or args.cri:
            print("\n[t10] Running CRI computation...")
            t10_cri.run_cri(all_results)

        if args.all or args.ecv:
            print("\n[Stage 06] Running External Consistency Validation...")
            s06.run_ecv(all_results)

    elif args.cri:
        # Load dari file CSV yang sudah ada
        print("[t10] CRI dari hasil yang sudah tersimpan...")
        # Implementasikan load dari CSV jika pipeline sudah pernah dijalankan
        pass

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
