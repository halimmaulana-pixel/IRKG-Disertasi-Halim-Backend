"""
Tier 2: Lexical Bridge Dictionary (127 terms)
Indonesian IT competency terms → English equivalents
Berdasarkan spesifikasi paper Section III.E
"""

BRIDGE_DICT = {
    # Pemrograman & Pengembangan
    "pemrograman": "programming",
    "pengembangan perangkat lunak": "software development",
    "pengembangan aplikasi": "application development",
    "pengembangan sistem": "system development",
    "pengembangan web": "web development",
    "pengembangan mobile": "mobile development",
    "rekayasa perangkat lunak": "software engineering",
    "pengujian perangkat lunak": "software testing",
    "pengujian sistem": "system testing",
    "kode program": "source code",
    "bahasa pemrograman": "programming language",
    "struktur data": "data structure",
    "algoritma": "algorithm",
    "pemrograman berorientasi objek": "object oriented programming",
    "antarmuka pengguna": "user interface",
    "antarmuka": "interface",

    # Infrastruktur & Jaringan
    "jaringan komputer": "computer network",
    "keamanan jaringan": "network security",
    "administrasi jaringan": "network administration",
    "infrastruktur jaringan": "network infrastructure",
    "pengelolaan jaringan": "network management",
    "arsitektur jaringan": "network architecture",
    "protokol jaringan": "network protocol",
    "keamanan siber": "cybersecurity",
    "keamanan informasi": "information security",
    "keamanan sistem": "system security",
    "enkripsi": "encryption",
    "firewall": "firewall",
    "virtualisasi": "virtualization",
    "komputasi awan": "cloud computing",
    "pusat data": "data center",
    "pengelolaan pusat data": "data center management",
    "server": "server",
    "basis data": "database",
    "pengelolaan basis data": "database management",
    "administrasi basis data": "database administration",

    # Kecerdasan Buatan & Data
    "kecerdasan buatan": "artificial intelligence",
    "pembelajaran mesin": "machine learning",
    "pembelajaran mendalam": "deep learning",
    "ilmu data": "data science",
    "analisis data": "data analysis",
    "penambangan data": "data mining",
    "visualisasi data": "data visualization",
    "pengolahan data": "data processing",
    "integrasi data": "data integration",
    "arsitektur data": "data architecture",
    "manajemen data": "data management",
    "tata kelola data": "data governance",
    "kualitas data": "data quality",
    "gudang data": "data warehouse",
    "pemrosesan bahasa alami": "natural language processing",
    "visi komputer": "computer vision",
    "sistem pakar": "expert system",
    "otomasi": "automation",
    "robotika": "robotics",

    # Sistem Informasi & Manajemen
    "sistem informasi": "information system",
    "sistem informasi manajemen": "management information system",
    "analisis sistem": "system analysis",
    "perancangan sistem": "system design",
    "arsitektur sistem": "system architecture",
    "integrasi sistem": "system integration",
    "implementasi sistem": "system implementation",
    "pengelolaan sistem": "system management",
    "audit sistem": "system audit",
    "dokumentasi sistem": "system documentation",
    "rekayasa sistem": "system engineering",
    "pemeliharaan sistem": "system maintenance",
    "operasional sistem": "system operations",
    "tata kelola teknologi informasi": "IT governance",
    "manajemen teknologi informasi": "IT management",
    "layanan teknologi informasi": "IT service",
    "dukungan teknologi informasi": "IT support",
    "infrastruktur teknologi informasi": "IT infrastructure",

    # Proses & Metodologi
    "metodologi pengembangan": "development methodology",
    "manajemen proyek": "project management",
    "perencanaan proyek": "project planning",
    "manajemen risiko": "risk management",
    "kontrol kualitas": "quality control",
    "jaminan kualitas": "quality assurance",
    "proses bisnis": "business process",
    "analisis kebutuhan": "requirements analysis",
    "rekayasa kebutuhan": "requirements engineering",
    "pengujian": "testing",
    "pemeliharaan": "maintenance",
    "penerapan": "deployment",
    "konfigurasi": "configuration",
    "manajemen konfigurasi": "configuration management",
    "kontrol versi": "version control",
    "siklus hidup": "lifecycle",
    "siklus hidup pengembangan perangkat lunak": "software development lifecycle",

    # Kompetensi Umum IT
    "pemecahan masalah": "problem solving",
    "berpikir analitis": "analytical thinking",
    "berpikir kritis": "critical thinking",
    "berpikir komputasional": "computational thinking",
    "literasi digital": "digital literacy",
    "transformasi digital": "digital transformation",
    "inovasi digital": "digital innovation",
    "kewirausahaan digital": "digital entrepreneurship",
    "komunikasi teknis": "technical communication",
    "dokumentasi teknis": "technical documentation",
    "desain teknis": "technical design",
    "spesifikasi teknis": "technical specification",

    # Pengguna & Layanan
    "pengalaman pengguna": "user experience",
    "kepuasan pengguna": "user satisfaction",
    "layanan pelanggan": "customer service",
    "dukungan pengguna": "user support",
    "pelatihan pengguna": "user training",
    "aksesibilitas": "accessibility",
    "kegunaan": "usability",

    # Regulasi & Standar
    "standar kompetensi": "competency standard",
    "sertifikasi": "certification",
    "akreditasi": "accreditation",
    "regulasi": "regulation",
    "kepatuhan": "compliance",
    "etika profesi": "professional ethics",
    "etika teknologi": "technology ethics",
    "hak kekayaan intelektual": "intellectual property",
    "privasi data": "data privacy",
    "perlindungan data": "data protection",

    # Hardware & Infrastruktur Fisik
    "perangkat keras": "hardware",
    "perangkat lunak": "software",
    "jaringan": "network",
    "komputer": "computer",
    "mikrokontroler": "microcontroller",
    "tertanam": "embedded",
    "sistem tertanam": "embedded system",
    "internet of things": "internet of things",
    "perangkat pintar": "smart device",

    # Organisasi & Bisnis
    "organisasi": "organization",
    "perusahaan": "enterprise",
    "bisnis": "business",
    "strategi": "strategy",
    "kepemimpinan": "leadership",
    "kerja sama tim": "teamwork",
    "kolaborasi": "collaboration",
    "komunikasi": "communication",
    "presentasi": "presentation",

    # Mobile Development (SKKNI J.612000 coverage)
    "perangkat mobile": "mobile device",
    "aplikasi mobile": "mobile application",
    "jaringan mobile": "mobile network",
    "sistem mobile": "mobile system",
    "perangkat wearable": "wearable device",
    "pemrograman jaringan": "network programming",
    "penyimpanan data": "data storage",
    "aplikasi pesan multimedia": "multimedia messaging application",
    "layanan berbasis lokasi": "location based service",
    "antarmuka pengguna": "user interface",
    "antarmuka": "interface",
    "keamanan komunikasi": "communication security",
    "ancaman keamanan": "security threat",
    "forensik digital": "digital forensics",
    "forensik": "forensics",
    "investigasi": "investigation",
    "aplikasi keuangan": "financial application",
    "aplikasi media digital": "digital media application",
    "kartu cerdas": "smart card",
    "smart card": "smart card NFC contactless",
    "smart city": "smart city IoT urban technology",
    "geofencing": "geofencing digital boundary",
    "iot": "IoT Internet of Things",
    "mekanisme": "mechanism",
    "spesifikasi teknis": "technical specification",
    "penguasaan": "mastery proficiency",
    "adaptasi": "adaptation migration",
    "insiden": "incident",

    # Wireless & IoT (SKKNI J.612000 coverage)
    "nirkabel": "wireless",
    "jaringan nirkabel": "wireless network",
    "protokol keamanan nirkabel": "wireless security protocol",
    "jaringan sensor nirkabel": "wireless sensor network",
    "sensor": "sensor IoT embedded",
    "jaringan wpan": "wireless personal area network WPAN",

    # Cloud Computing (SKKNI J.63HOS00 coverage)
    "layanan cloud": "cloud service",
    "sistem cloud": "cloud system",
    "skalabel": "scalable",
    "sla": "SLA service level agreement",
    "sarana prasarana": "infrastructure",
    "layanan berbasis cloud": "cloud based service",
    "topologi jaringan": "network topology",

    # API & Integration
    "api": "API application programming interface",

    "negosiasi": "negotiation",
}

# Tier 1: shared IT terms (code-switching — same in Indonesian and English)
SHARED_IT_TERMS = [
    "database", "server", "network", "algorithm", "software",
    "hardware", "internet", "cloud", "data", "system", "interface",
    "framework", "platform", "application", "mobile", "web",
    "API", "backend", "frontend", "DevOps", "agile", "scrum",
    "Linux", "Windows", "Python", "Java", "SQL", "HTML", "CSS",
    "JavaScript", "machine learning", "deep learning", "AI",
    "cybersecurity", "blockchain", "IoT", "ERP", "CRM",
    "firewall", "router", "switch", "protocol", "encryption",
]


def apply_bridge(text: str) -> str:
    """
    Apply two-tier cross-lingual bridge to Indonesian text.
    Tier 1: shared IT terms remain unchanged
    Tier 2: apply lexical bridge dictionary
    Returns English-friendly text for TF-IDF vectorization.

    Fix: uses regex word boundaries to prevent partial substring replacement.
    E.g. "basis data" must not match inside "berbasis data" -> "berdatabase".
    """
    import re
    if not isinstance(text, str):
        return ""
    text_lower = text.lower()
    # Apply Tier 2: sorted by length (longest first to avoid partial replacement)
    for id_term, en_term in sorted(BRIDGE_DICT.items(), key=lambda x: -len(x[0])):
        # Use word boundary-aware replacement:
        # \b works for alphanumeric edges; for phrases starting/ending with
        # word chars we wrap with (?<!\w) / (?!\w) lookarounds to be safe
        pattern = r'(?<![a-zA-Z0-9])' + re.escape(id_term) + r'(?![a-zA-Z0-9])'
        text_lower = re.sub(pattern, en_term, text_lower)
    return text_lower
