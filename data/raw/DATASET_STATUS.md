# IR-KG Dataset Status Report
**Framework:** Hybrid Information Retrieval–Knowledge Graph for Cross-Framework Competency Mapping  
**Project:** CPL × SKKNI × ESCO × O\*NET  
**Universitas Sumatera Utara — Halim Maulana et al.**  
**Audit Date:** 2026-03-02  

---

## Struktur Folder

```
irkg_dataset/
├── source_data/          # Data sumber utama (CPL, SKKNI, O*NET)
│   ├── cpl_si.xlsx
│   ├── cpl_ti.xlsx
│   ├── skkni_enriched.csv
│   └── onet_occupations.csv
│
├── esco/                 # ESCO v1.1 dataset lengkap
│   ├── esco_skills.csv
│   ├── esco_occupations.csv
│   ├── esco_skills_hierarchy.csv
│   ├── esco_skill_groups.csv
│   ├── esco_isco_groups.csv
│   └── esco_ontology_schema.rdf
│
├── graph_relations/      # Relasi untuk Graph Reasoning (S_gr)
│   ├── occ_skill_relations.csv
│   ├── skill_skill_relations.csv
│   ├── skill_broader_relations.csv
│   └── occ_broader_relations.csv
│
├── bridge/               # Cross-lingual bridge dictionary
│   └── bridge_dict.py
│
└── DATASET_STATUS.md     # File ini
```

---

## 1. SOURCE DATA

### 1.1 CPL — Capaian Pembelajaran Lulusan

| Properti | CPL SI | CPL TI |
|----------|--------|--------|
| File | `source_data/cpl_si.xlsx` | `source_data/cpl_ti.xlsx` |
| File asli | `cpl_si.xlsx` | `cpl_ti.xlsx` |
| Rows | **15** | **15** |
| Total CPL | **30 items** | |
| Size | 10 KB | 10 KB |
| Null | 0 | 0 |
| Bahasa | Bahasa Indonesia | Bahasa Indonesia |
| Status | ✅ READY | ✅ READY |

**Kolom:**
| Kolom | Keterangan | Digunakan Pipeline |
|-------|-----------|-------------------|
| `id_cpl` | ID unik (PLO-1 s/d PLO-15) | ✅ → dijadikan `id` dengan prefix program |
| `ranah` | Sikap / Pengetahuan / Keterampilan Umum / Keterampilan Khusus | ✅ metadata |
| `deskripsi_cpl` | Deskripsi CPL dalam Bahasa Indonesia | ✅ teks utama TF-IDF |
| `mata_kuliah_terkait` | Nama mata kuliah terkait | ❌ tidak digunakan |
| `level_kkni` | Level KKNI (semua = 6) | ✅ metadata |

**Distribusi Ranah:**
- CPL SI: Keterampilan Khusus (6), Sikap (3), Pengetahuan (3), Keterampilan Umum (3)
- CPL TI: Pengetahuan (6), Sikap (3), Keterampilan Umum (3), Keterampilan Khusus (3)

**Catatan:** ID gabungan akan dibuat sebagai `SI_PLO-1`, `TI_PLO-1`, dst.

---

### 1.2 SKKNI — Standar Kompetensi Kerja Nasional Indonesia

| Properti | Detail |
|----------|--------|
| File | `source_data/skkni_enriched.csv` |
| File asli | `skkni_clean_enriched_v4.csv` |
| Rows | **1.711** |
| Size | 743 KB |
| Null | 0 (semua text kolom) |
| Bahasa | Indonesia + campuran EN (enriched) |
| Status | ✅ READY |

**Kolom:**
| Kolom | Keterangan | Digunakan Pipeline |
|-------|-----------|-------------------|
| `kode_unit` | Kode unit kompetensi (ex: J.62DPM00.002.1) | ✅ sebagai `id` |
| `judul_unit` | Judul unit kompetensi | ✅ metadata |
| `deskripsi_unit_clean` | Deskripsi dalam Bahasa Indonesia | ✅ untuk T3 (CPL→SKKNI, monolingual) |
| `deskripsi_unit_clean_nlp` | Versi NLP-preprocessed dari clean | referensi |
| `deskripsi_unit_enriched` | **Deskripsi semi-English** (mixed code-switching) | ✅ **teks utama untuk T4, T5** (cross-lingual) |
| `deskripsi_unit_enriched_nlp` | Versi NLP dari enriched | referensi |
| `level_kkni` | Level KKNI | ⚠️ semua NULL — tidak digunakan |
| `doc_sector` | Sektor industri SKKNI | ✅ metadata (60 sektor unik) |
| `doc_title` | Judul dokumen SKKNI | ✅ metadata |

**Distribusi Prefix Kode Unit:**
| Prefix | Jumlah | Keterangan |
|--------|--------|-----------|
| `J.` | 1.590 | Mayoritas — IT/Informatika |
| `TI` | 64 | Teknologi Informasi |
| `M.` | 34 | Multimedia |
| `K.` | 12 | Komunikasi |
| `IC` | 6 | ICT |
| `MS` | 3 | Mixed |
| `H.` | 2 | Lainnya |

**Top Sektor (dari 60 sektor):**
Telekomunikasi (148), Penggelaran Jaringan Seluler (126), Keahlian Pengembangan Video Game (82), Animasi (80), Keamanan Informasi (67), Penerbitan Buku (59)

> ⚠️ **Catatan penting:** `level_kkni` seluruhnya NULL (1711/1711). Ini **tidak berpengaruh** pada pipeline karena kolom ini tidak digunakan untuk TF-IDF atau scoring.

> ✅ **Keunggulan v4:** `deskripsi_unit_enriched` sudah mengandung terminologi IT dalam bahasa Inggris secara alami (code-switching). Ini sangat menguntungkan untuk cross-lingual TF-IDF karena TF-IDF dapat langsung menemukan kesamaan kata dengan ESCO/O*NET tanpa full translation.

---

### 1.3 O\*NET — Occupational Information Network

| Properti | Detail |
|----------|--------|
| File | `source_data/onet_occupations.csv` |
| File asli | `onet_all_occupations_final.csv` |
| Rows | **879** |
| Size | 1.3 MB |
| Null | 0 (semua kolom) |
| Bahasa | English |
| Status | ✅ READY |

**Kolom:**
| Kolom | Keterangan | Digunakan Pipeline |
|-------|-----------|-------------------|
| `soc_code` | SOC code occupation (ex: 15-1252.00) | ✅ sebagai `id` |
| `title` | Nama occupation | ✅ metadata |
| `major_group_code` | Kode major group (11, 13, 15, ..., 53) | ✅ metadata domain |
| `onet_text_enriched` | Teks gabungan: title + domain + skills (English) | ✅ **teks utama TF-IDF** |
| `onet_text_nlp` | Versi NLP-preprocessed | referensi |

**Statistik teks:**
- `onet_text_enriched`: min=75 kata, rata-rata=78 kata, max=84 kata (konsisten)
- 22 major group codes tercakup

> ✅ `onet_text_enriched` sudah merupakan dokumen yang diperkaya dengan title + domain keywords + skill types — ideal untuk TF-IDF occupational matching.

---

## 2. ESCO v1.1 DATASET

### 2.1 ESCO Skills

| Properti | Detail |
|----------|--------|
| File | `esco/esco_skills.csv` |
| File asli | `skills_en.csv` |
| Rows | **13.939** |
| Size | 8.9 MB |
| Null | `description`: 0, `preferredLabel`: 0, `definition`: 13.936 (hampir semua — tidak digunakan) |
| Bahasa | English |
| Status | ✅ READY |

**Kolom utama yang digunakan:**
| Kolom | Keterangan | Digunakan Pipeline |
|-------|-----------|-------------------|
| `conceptUri` | URI unik ESCO | ✅ sebagai ID graph |
| `preferredLabel` | Label skill (ex: "use programming tools") | ✅ bagian teks TF-IDF |
| `description` | Deskripsi lengkap skill | ✅ **teks utama TF-IDF** |
| `skillType` | skill/competence (10.715) atau knowledge (3.219) | ✅ metadata |
| `status` | Semua = `released` | ✅ semua valid |

**Teks TF-IDF yang dibangun:** `preferredLabel + " " + description` → rata-rata 26 kata/skill

> ⚠️ **Catatan implementasi:** `data_loader.py` perlu menyambung `preferredLabel` + `description` karena tidak ada kolom `skill_text_clean` (nama asli di file berbeda dari yang diexpect kode).

---

### 2.2 ESCO Occupations

| Properti | Detail |
|----------|--------|
| File | `esco/esco_occupations.csv` |
| File asli | `occupations_en.csv` |
| Rows | **3.039** |
| Size | 2.7 MB |
| Null | 0 untuk `preferredLabel`, `description`, `code` |
| Status | ✅ READY |

**Catatan:** Digunakan sebagai konteks graph reasoning (bukan target TF-IDF langsung). ID sebaiknya dari `conceptUri` bukan `code` karena format `code` tidak standar (ex: `2654.1.7`).

---

### 2.3 ESCO Skills Hierarchy

| File | Rows | Keterangan |
|------|------|-----------|
| `esco/esco_skills_hierarchy.csv` | 640 | Hierarki 4-level (Level 0–3) |
| `esco/esco_skill_groups.csv` | 640 | Skill groups dengan scope notes |
| `esco/esco_isco_groups.csv` | 619 | ISCO occupation groups |
| `esco/esco_ontology_schema.rdf` | 177 KB | OWL ontology schema (bukan instance data) |

> ⚠️ **Catatan `esco_ontology_schema.rdf`:** File ini adalah **OWL schema** (class/property definitions), **bukan** instance relation graph. Relasi antar skill (isRelatedTo, broaderSkillOf, dll.) yang disebut dalam paper sebenarnya ada di file `graph_relations/`. Pipeline menggunakan pendekatan Dice coefficient keyword overlap sebagai pengganti path-length graph traversal.

---

## 3. GRAPH RELATIONS (untuk S_gr)

| File | Rows | Size | URI Match ke Skills | Status |
|------|------|------|---------------------|--------|
| `occ_skill_relations.csv` | **65.537** | 10.7 MB | 100% | ✅ READY |
| `skill_skill_relations.csv` | **5.818** | 969 KB | 100% | ✅ READY |
| `skill_broader_relations.csv` | **20.822** | 3.5 MB | 95.6% | ✅ READY |
| `occ_broader_relations.csv` | **3.652** | 504 KB | — | ✅ READY |

### Detail Setiap File

**`occ_skill_relations.csv`** — Relasi occupation ↔ skill
- Kolom: `occupationUri`, `relationType`, `skillType`, `skillUri`
- relationType: `essential` (34.382) + `optional` (31.155)
- Mencakup 1.557 occupation unik → 11.360 skill unik
- **Digunakan untuk:** membangun graph co-occurrence untuk S_gr

**`skill_skill_relations.csv`** — Relasi skill ↔ skill
- Kolom: `originalSkillUri`, `originalSkillType`, `relationType`, `relatedSkillType`, `relatedSkillUri`
- relationType: `optional` (5.629) + `essential` (189)
- **Digunakan untuk:** path traversal antar skill di graph

**`skill_broader_relations.csv`** — Hierarki broader skill
- Kolom: `conceptType`, `conceptUri`, `broaderType`, `broaderUri`
- conceptType: `KnowledgeSkillCompetence` (20.186) + `SkillGroup` (636)
- 95.6% URI match ke `esco_skills.csv` (sisa 4.4% adalah SkillGroup URI)
- **Digunakan untuk:** hierarki skill untuk constraint reasoning

**`occ_broader_relations.csv`** — Hierarki broader occupation
- Kolom: `conceptType`, `conceptUri`, `broaderType`, `broaderUri`
- 3.652 relasi hierarki occupation

---

## 4. BRIDGE DICTIONARY

| File | Keterangan | Status |
|------|-----------|--------|
| `bridge/bridge_dict.py` | Cross-lingual bridge ID→EN | ✅ READY |

**Statistik:**
- `BRIDGE_DICT`: **177 term pairs** (Indonesian → English)
- `SHARED_IT_TERMS`: **43 terms** (teknis IT yang sama di kedua bahasa)
- Fungsi: `apply_bridge(text: str) -> str`

**Contoh mapping:**
```
pemrograman              → programming
pengembangan perangkat lunak → software development
basis data               → database
keamanan informasi       → information security
kecerdasan buatan        → artificial intelligence
```

> **Catatan:** Paper menyebut 127 terms, `bridge_dict.py` berisi 177 terms — sudah diperluas. Ini lebih baik karena coverage lebih luas.

---

## 5. MAPPING TASKS & DATASET YANG DIGUNAKAN

| Task | Mapping | Source File | Target File | Cross-Lingual | Corpus Size |
|------|---------|-------------|-------------|---------------|-------------|
| T1 | CPL → ESCO Skills | `cpl_si/ti.xlsx` | `esco_skills.csv` | ✅ ID→EN | 13.969 docs |
| T2 | CPL → O\*NET | `cpl_si/ti.xlsx` | `onet_occupations.csv` | ✅ ID→EN | 909 docs |
| T3 | CPL → SKKNI | `cpl_si/ti.xlsx` | `skkni_enriched.csv` | ❌ ID→ID | 1.741 docs |
| T4 | SKKNI → ESCO Skills | `skkni_enriched.csv` | `esco_skills.csv` | ✅ ID→EN | 15.650 docs |
| T5 | SKKNI → O\*NET | `skkni_enriched.csv` | `onet_occupations.csv` | ✅ ID→EN | 2.590 docs |

**Total kandidat yang akan di-generate (top-k=20):**
- T1: 30 × 20 = 600 kandidat
- T2: 30 × 20 = 600 kandidat
- T3: 30 × 20 = 600 kandidat
- T4: 1.711 × 20 = 34.220 kandidat
- T5: 1.711 × 20 = 34.220 kandidat
- **TOTAL: 70.240 kandidat pairs**

---

## 6. BUG CODE YANG PERLU DIPERBAIKI SEBELUM IMPLEMENTASI

> Dataset sudah benar. Bug berada di sisi **kode**, bukan data.

| # | File | Bug | Fix |
|---|------|-----|-----|
| 1 | `data_loader.py` | Import `from crosslingual.bridge_dict import apply_bridge` — folder tidak ada | Ganti ke `from bridge_dict import apply_bridge` |
| 2 | `data_loader.py` | Path SKKNI: `skkni_clean.csv` — file tidak ada | Ganti ke `skkni_enriched.csv` |
| 3 | `data_loader.py` | `load_skkni()` menggunakan kolom `deskripsi_unit_clean` | Gunakan `deskripsi_unit_enriched` untuk T4/T5 cross-lingual |
| 4 | `data_loader.py` | Path ESCO: `esco_skills_clean.csv` — file tidak ada | Ganti ke `esco/esco_skills.csv` + gabung `preferredLabel + description` |
| 5 | `data_loader.py` | Path ESCO Occ: `esco_occupations_clean.csv` — file tidak ada | Ganti ke `esco/esco_occupations.csv` + gunakan `conceptUri` sebagai ID |
| 6 | `data_loader.py` | Path O\*NET: `onet_skills_clean.csv` — file tidak ada | Ganti ke `source_data/onet_occupations.csv` |
| 7 | `graph_constraint.py` | Constraint rule O\*NET prefix `"ONET"` — ID sebenarnya format soc_code `"15-1252.00"` | Ganti ke check berdasarkan `target_source == "ONET"` |
| 8 | `graph_constraint.py` | Constraint rule SKKNI prefix hanya `"J."` — ada 121 SKKNI dengan prefix lain (TI, M., K., dll.) | Tambah semua prefix valid atau gunakan check berbeda |

---

## 7. RINGKASAN STATUS KESELURUHAN

```
✅ SOURCE DATA    : LENGKAP — CPL (30), SKKNI (1711), O*NET (879)
✅ ESCO DATASET   : LENGKAP — Skills (13939), Occupations (3039)
✅ GRAPH RELATIONS: LENGKAP — 95.000+ relasi, URI match 100%
✅ BRIDGE DICT    : LENGKAP — 177 terms, apply_bridge() berfungsi
❌ PIPELINE CODE  : ADA 8 BUG — perlu fix sebelum run
```

**Dataset siap untuk implementasi setelah 8 bug di kode diperbaiki.**

---

*Dibuat oleh: Dataset Audit IR-KG Framework — 2026-03-02*
