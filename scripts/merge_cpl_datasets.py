"""
Merge semua CPL dataset ke dalam cpl_si.xlsx dan cpl_ti.xlsx yang sudah ada.

Pengelompokan:
  SI group: UMSU SI (prefix UMSU) + UI SI (prefix UI)
  TI group: UMSU TI (prefix UMSU) + ITK Informatika (prefix ITK)
            + PENS Teknik Komputer (prefix PENS) + UGM TI (prefix UGM)

id_cpl baru: {UNIV}_PLO-N  →  semua unik
Backup file lama dibuat dulu sebelum overwrite.
"""
import shutil
import pandas as pd
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "data" / "raw" / "source_data"


def load_with_prefix(filename: str, prefix: str) -> pd.DataFrame:
    df = pd.read_excel(SRC / filename)
    df["id_cpl"] = prefix + "_" + df["id_cpl"]
    df["univ"]   = prefix
    return df[["id_cpl", "ranah", "deskripsi_cpl", "mata_kuliah_terkait", "level_kkni", "univ"]]


# ── Backup file asli ──────────────────────────────────────────────────────
for fname in ("cpl_si.xlsx", "cpl_ti.xlsx"):
    src = SRC / fname
    bak = SRC / fname.replace(".xlsx", "_backup.xlsx")
    if not bak.exists():
        shutil.copy2(src, bak)
        print(f"[BACKUP] {fname} -> {bak.name}")
    else:
        print(f"[SKIP backup] {bak.name} sudah ada")

# ── SI group: UMSU_SI + UI_SI ─────────────────────────────────────────────
print("\n[SI group]")
parts_si = [
    load_with_prefix("cpl_si.xlsx",    "UMSU"),
    load_with_prefix("cpl_ui_si.xlsx", "UI"),
]
df_si = pd.concat(parts_si, ignore_index=True)

# Reset nomor PLO berurutan per univ
df_si_out = df_si.drop(columns=["univ"])
df_si_out.to_excel(SRC / "cpl_si.xlsx", index=False)

print(f"  Total: {len(df_si)} CPL items")
print(f"  Dari: {df_si.groupby('univ').size().to_dict()}")
print(f"  Ranah: {df_si['ranah'].value_counts().to_dict()}")

# ── TI group: UMSU_TI + ITK + PENS + UGM ────────────────────────────────
print("\n[TI group]")
parts_ti = [
    load_with_prefix("cpl_ti.xlsx",           "UMSU"),
    load_with_prefix("cpl_itk_informatika.xlsx", "ITK"),
    load_with_prefix("cpl_pens_tekkom.xlsx",   "PENS"),
    load_with_prefix("cpl_ugm_ti.xlsx",        "UGM"),
]
df_ti = pd.concat(parts_ti, ignore_index=True)

df_ti_out = df_ti.drop(columns=["univ"])
df_ti_out.to_excel(SRC / "cpl_ti.xlsx", index=False)

print(f"  Total: {len(df_ti)} CPL items")
print(f"  Dari: {df_ti.groupby('univ').size().to_dict()}")
print(f"  Ranah: {df_ti['ranah'].value_counts().to_dict()}")

# ── Preview ───────────────────────────────────────────────────────────────
print("\n=== Preview cpl_si.xlsx ===")
df_check = pd.read_excel(SRC / "cpl_si.xlsx")
print(df_check[["id_cpl", "ranah", "deskripsi_cpl"]].to_string())

print("\n=== Preview cpl_ti.xlsx (10 pertama) ===")
df_check2 = pd.read_excel(SRC / "cpl_ti.xlsx")
print(df_check2[["id_cpl", "ranah", "deskripsi_cpl"]].head(10).to_string())
print(f"  ... dan {len(df_check2)-10} baris lainnya")

print("\n[DONE] cpl_si.xlsx dan cpl_ti.xlsx sudah diperbarui.")
print(f"  SI: {len(df_si)} items | TI: {len(df_ti)} items")
