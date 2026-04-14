"""
Create CPL datasets from external universities for cross-institution testing.
Sources:
- ITK (Institut Teknologi Kalimantan) - S1 Informatika
- UI  (Universitas Indonesia, Fasilkom) - S1 Sistem Informasi
- PENS (Politeknik Elektronika Negeri Surabaya) - D4 Teknik Komputer
- UGM JTETI (Universitas Gadjah Mada) - S1 Teknologi Informasi
"""
import pandas as pd
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "raw" / "source_data"
OUT.mkdir(parents=True, exist_ok=True)

# ─── 1. ITK — Informatika ──────────────────────────────────────────────────
# Source: if.itk.ac.id/akademik/capaian_pembelajaran_lulusan
cpl_itk = [
    ("PLO-1",  "Keterampilan Umum",
     "Mampu berkomunikasi efektif secara lisan dan tulisan dengan audiens yang bervariasi."),
    ("PLO-2",  "Keterampilan Khusus",
     "Mampu mengidentifikasi, merumuskan, menganalisa, menyelesaikan permasalahan kompleks, serta mengambil keputusan dengan mempertimbangkan dampaknya pada aspek hukum, ekonomi, lingkungan, sosial, politik, kesehatan, keselamatan, dan keberlanjutan serta memanfaatkan teknologi informasi dan potensi sumber daya nasional dalam perspektif global."),
    ("PLO-3",  "Keterampilan Umum",
     "Mampu berkolaborasi secara efektif dalam tim multi disiplin dan budaya yang beragam, serta bersama-sama memiliki jiwa kepemimpinan untuk mencapai tujuan."),
    ("PLO-4",  "Sikap",
     "Mampu mengaplikasikan nilai Pancasila, etika dan tanggung jawab profesional."),
    ("PLO-5",  "Keterampilan Umum",
     "Mampu menunjukkan kemampuan belajar sepanjang hayat dan menerapkan pengetahuan tersebut sesuai kebutuhan dengan strategi pembelajaran yang tepat."),
    ("PLO-6",  "Pengetahuan",
     "Mampu memahami konsep matematika, statistika, struktur diskrit, struktur data dan algoritma, dalam menyelesaikan berbagai masalah berkaitan dengan keteknikan dengan prinsip-prinsip komputasi secara efektif dan efisien."),
    ("PLO-7",  "Pengetahuan",
     "Mampu menerapkan rekayasa sistem dengan mempertimbangkan kemampuan perangkat keras dan sistem operasi."),
    ("PLO-8",  "Pengetahuan",
     "Menerapkan konsep-konsep yang berkaitan dengan arsitektur, organisasi komputer, jaringan, dan basis data serta memanfaatkannya sebagai penunjang dalam pengembangan sistem."),
    ("PLO-9",  "Keterampilan Khusus",
     "Mampu mengintegrasikan prinsip pengembangan sistem pada bidang kecerdasan artifisial, sistem benam, dan perangkat lunak meliputi analisis dan desain sistem, implementasi dan pengujian, serta penjaminan mutu dari sistem."),
    ("PLO-10", "Keterampilan Khusus",
     "Mampu menganalisis dan mengimplementasikan konsep sains data, sistem cerdas, dan visi komputer dalam menyelesaikan permasalahan ketahanan pangan, energi, maritim dan smart city."),
    ("PLO-11", "Keterampilan Khusus",
     "Mampu mengimplementasikan konsep bisnis rintisan digital berbasis teknologi informasi."),
    ("PLO-12", "Sikap",
     "Mampu menerapkan etika profesional bidang ilmu komputer."),
]
df = pd.DataFrame(cpl_itk, columns=["id_cpl", "ranah", "deskripsi_cpl"])
df["mata_kuliah_terkait"] = ""
df["level_kkni"] = 6
df.to_excel(OUT / "cpl_itk_informatika.xlsx", index=False)
print(f"[OK] ITK Informatika: {len(df)} CPL")

# ─── 2. UI — Sistem Informasi ─────────────────────────────────────────────
# Source: cs.ui.ac.id/en/sarjana-sistem-informasi/
cpl_ui = [
    ("PLO-1",  "Sikap",
     "Mampu menunjukkan kepekaan terhadap isu lingkungan dan sosial dalam kerangka kebangsaan Indonesia berdasarkan Pancasila."),
    ("PLO-2",  "Keterampilan Umum",
     "Mampu menggunakan teknologi informasi dan komunikasi secara bijaksana dalam lingkungan akademik maupun profesional."),
    ("PLO-3",  "Keterampilan Umum",
     "Mampu berkomunikasi secara efektif dalam Bahasa Indonesia dan/atau Bahasa Inggris untuk kegiatan akademik dan non-akademik."),
    ("PLO-4",  "Keterampilan Umum",
     "Mampu menerapkan penalaran kritis, sistematis, dan logis dalam menganalisis dan merumuskan masalah sesuai kaidah ilmiah untuk menghasilkan solusi komputasi."),
    ("PLO-5",  "Keterampilan Umum",
     "Mampu berkomunikasi secara efektif, bekerja sama dan berkontribusi dalam tim dengan berbagai latar belakang dalam memberikan solusi berbasis teknologi informasi di bidang profesional."),
    ("PLO-6",  "Sikap",
     "Mampu menerapkan etika profesional secara konsisten dengan memperhatikan isu hukum, keamanan, dan sosial dalam pemanfaatan teknologi informasi untuk pemecahan masalah."),
    ("PLO-7",  "Keterampilan Umum",
     "Mampu beradaptasi dalam mengikuti perkembangan teknologi informasi untuk pengembangan profesional secara berkelanjutan."),
    ("PLO-8",  "Keterampilan Khusus",
     "Mampu mengidentifikasi, merencanakan, merancang, dan mengevaluasi solusi SI/TI yang sesuai dengan kebutuhan organisasi berdasarkan prinsip-prinsip keilmuan."),
    ("PLO-9",  "Keterampilan Khusus",
     "Mampu memilih dan menerapkan teknik dan alat yang tepat dalam menyelesaikan permasalahan organisasi berbasis sistem informasi."),
    ("PLO-10", "Keterampilan Khusus",
     "Mampu mengelola sistem informasi dan teknologi dalam suatu organisasi, meliputi manajemen server, basis data, infrastruktur, layanan TI, dan audit sistem informasi."),
    ("PLO-11", "Keterampilan Khusus",
     "Mampu mengelola sistem informasi dan teknologi informasi skala enterprise untuk mendukung proses bisnis, termasuk manajemen pengetahuan, integrasi aplikasi, e-commerce, dan business intelligence."),
    ("PLO-12", "Pengetahuan",
     "Mampu berpikir kritis, logis, kreatif, dan inovatif, serta memiliki rasa ingin tahu intelektual dalam memecahkan masalah secara individu maupun kelompok."),
]
df = pd.DataFrame(cpl_ui, columns=["id_cpl", "ranah", "deskripsi_cpl"])
df["mata_kuliah_terkait"] = ""
df["level_kkni"] = 6
df.to_excel(OUT / "cpl_ui_si.xlsx", index=False)
print(f"[OK] UI Sistem Informasi: {len(df)} CPL")

# ─── 3. PENS — Teknik Komputer ────────────────────────────────────────────
# Source: tekkom.pens.ac.id/cpl/
cpl_pens = [
    ("PLO-1",  "Sikap",
     "Bertaqwa kepada Tuhan Yang Maha Esa dan mampu menunjukkan sikap religius dalam kehidupan profesional."),
    ("PLO-2",  "Sikap",
     "Menjunjung tinggi nilai kemanusiaan dalam menjalankan tugas berdasarkan agama, moral dan etika profesi."),
    ("PLO-3",  "Sikap",
     "Berkontribusi dalam peningkatan mutu kehidupan bermasyarakat, berbangsa, bernegara, dan peradaban berdasarkan Pancasila."),
    ("PLO-4",  "Sikap",
     "Menghargai keanekaragaman budaya, pandangan, agama, dan kepercayaan, serta pendapat orisinal orang lain dalam lingkungan kerja."),
    ("PLO-5",  "Sikap",
     "Bekerja sama dan memiliki kepekaan sosial serta kepedulian terhadap masyarakat dan lingkungan."),
    ("PLO-6",  "Sikap",
     "Menunjukkan sikap bertanggung jawab atas pekerjaan di bidang keahliannya secara mandiri."),
    ("PLO-7",  "Keterampilan Umum",
     "Menerapkan pemikiran logis, kritis, inovatif, bermutu, dan terukur dalam pekerjaan spesifik di bidang keahlian berdasarkan prosedur baku."),
    ("PLO-8",  "Keterampilan Umum",
     "Mampu menunjukkan kinerja mandiri, bermutu, dan terukur serta bertanggung jawab atas pencapaian hasil kerja kelompok."),
    ("PLO-9",  "Keterampilan Umum",
     "Mampu mengambil keputusan secara tepat berdasarkan prosedur baku, spesifikasi desain, dan persyaratan keselamatan kerja."),
    ("PLO-10", "Keterampilan Umum",
     "Mampu melakukan proses evaluasi diri terhadap kelompok kerja dan mengelola pembelajaran secara mandiri."),
    ("PLO-11", "Keterampilan Khusus",
     "Mampu menerapkan sains, elektronika dan kecerdasan buatan pada pengembangan robotika dan sistem cerdas berbasis komputasi."),
    ("PLO-12", "Keterampilan Khusus",
     "Mampu menerapkan komputasi waktu nyata untuk meningkatkan komunikasi cepat pada sistem operasi waktu nyata."),
    ("PLO-13", "Keterampilan Khusus",
     "Mampu menyelesaikan permasalahan di masyarakat dan lingkungan menggunakan teknologi sistem benam dan IoT."),
    ("PLO-14", "Keterampilan Khusus",
     "Mampu menerapkan prinsip dasar jaringan komputer dan menyelesaikan permasalahan terkait konektivitas jaringan."),
    ("PLO-15", "Pengetahuan",
     "Menguasai konsep teoretis matematika dan dasar rekayasa untuk memecahkan masalah komputasi dan robotika."),
    ("PLO-16", "Pengetahuan",
     "Menguasai teknologi sensor, pengenalan pola, computer vision, dan pemrograman mesin untuk sistem cerdas."),
    ("PLO-17", "Pengetahuan",
     "Menguasai fundamental jaringan komputer untuk memecahkan permasalahan kecepatan, keamanan, dan kehandalan jaringan."),
]
df = pd.DataFrame(cpl_pens, columns=["id_cpl", "ranah", "deskripsi_cpl"])
df["mata_kuliah_terkait"] = ""
df["level_kkni"] = 6
df.to_excel(OUT / "cpl_pens_tekkom.xlsx", index=False)
print(f"[OK] PENS Teknik Komputer: {len(df)} CPL")

# ─── 4. UGM JTETI — Teknologi Informasi ───────────────────────────────────
# Source: sarjana.jteti.ugm.ac.id/student-outcomes/ — diterjemahkan ke ID
cpl_ugm = [
    ("PLO-1",  "Pengetahuan",
     "Mampu menerapkan teori sains alam, matematika, dan rekayasa serta bidang lain yang relevan untuk memecahkan permasalahan rekayasa kompleks di bidang teknologi informasi."),
    ("PLO-2",  "Keterampilan Khusus",
     "Mampu mengidentifikasi permasalahan rekayasa dan menggunakan pendekatan, sumber daya, serta peralatan yang tepat untuk menyelesaikan permasalahan rekayasa yang kompleks."),
    ("PLO-3",  "Keterampilan Khusus",
     "Mampu merancang sistem, komponen, atau proses untuk memenuhi kebutuhan yang diinginkan dalam kendala realistis seperti ekonomi, lingkungan, sosial, politik, etika, kesehatan dan keselamatan, serta keberlanjutan."),
    ("PLO-4",  "Keterampilan Khusus",
     "Mampu merancang dan melaksanakan eksperimen untuk mengeksplorasi permasalahan rekayasa kompleks serta menganalisis dan menginterpretasikan data hasil eksperimen."),
    ("PLO-5",  "Keterampilan Khusus",
     "Mampu menggunakan teknik rekayasa, keterampilan, alat rekayasa modern, dan teknologi informasi untuk praktik rekayasa yang kompleks."),
    ("PLO-6",  "Keterampilan Umum",
     "Mampu berpikir logis untuk mengevaluasi isu kesehatan, sosial, keselamatan, hukum, atau budaya dalam konteks pengetahuan dan ilmu terkini."),
    ("PLO-7",  "Keterampilan Umum",
     "Mampu berkomunikasi secara efektif dan percaya diri dalam melaksanakan kegiatan rekayasa yang kompleks."),
    ("PLO-8",  "Keterampilan Umum",
     "Mampu berperan secara efektif sebagai individu dan anggota tim untuk mencapai tujuan bersama dalam lingkungan multidisiplin."),
    ("PLO-9",  "Sikap",
     "Menunjukkan komitmen etika terhadap norma, tanggung jawab, dan perilaku profesional rekayasa, dengan menginternalisasi nilai-nilai Pancasila dan kearifan lokal dalam konteks Indonesia."),
    ("PLO-10", "Pengetahuan",
     "Memiliki wawasan yang luas untuk memahami dampak solusi rekayasa dalam konteks global, ekonomi, lingkungan, dan kemasyarakatan."),
    ("PLO-11", "Keterampilan Umum",
     "Mampu menyadari pentingnya pembelajaran sepanjang hayat dan mampu melaksanakannya secara konsisten untuk pengembangan profesional di bidang teknologi informasi."),
]
df = pd.DataFrame(cpl_ugm, columns=["id_cpl", "ranah", "deskripsi_cpl"])
df["mata_kuliah_terkait"] = ""
df["level_kkni"] = 6
df.to_excel(OUT / "cpl_ugm_ti.xlsx", index=False)
print(f"[OK] UGM Teknologi Informasi: {len(df)} CPL")

print("\nSelesai. File tersimpan di:", OUT)
