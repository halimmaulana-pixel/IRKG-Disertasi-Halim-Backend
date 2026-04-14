# backend/models.py
from sqlalchemy import Column, String, Float, Integer, Boolean, Text, UniqueConstraint, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class CPLItem(Base):
    __tablename__ = "cpl_items"
    id = Column(String, primary_key=True)
    prodi = Column(String)
    ranah = Column(String)
    deskripsi = Column(Text)
    bridged_text = Column(Text)
    is_custom = Column(Boolean, default=False)

class CRIResult(Base):
    __tablename__ = "cri_results"
    source_id = Column(String, primary_key=True)
    prodi = Column(String)
    ranah = Column(String)
    r_esco = Column(Float)
    r_onet = Column(Float)
    r_skkni = Column(Float)
    cri_score = Column(Float)
    cri_flag = Column(String)
    top_esco_label = Column(String)
    top_esco_score = Column(Float)
    top_onet_label = Column(String)
    top_onet_score = Column(Float)
    top_skkni_label = Column(String)
    top_skkni_score = Column(Float)
    n_ok_esco = Column(Integer)
    n_ok_onet = Column(Integer)
    n_ok_skkni = Column(Integer)
    config_basis = Column(String)

class AblationResult(Base):
    __tablename__ = "ablation_results"
    __table_args__ = (
        UniqueConstraint("task", "config", "esco_target", name="uq_ablation_task_config_target"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    task = Column(String)
    config = Column(String)
    config_name = Column(String)
    esco_target = Column(Boolean)
    acceptance_rate = Column(Float)
    source_coverage = Column(Float)
    mean_final_score = Column(Float)
    forced_top1_ratio = Column(Float)
    selection_objective = Column(Float)

class AcceptedMapping(Base):
    __tablename__ = "accepted_mappings"
    __table_args__ = (
        UniqueConstraint(
            "source_id", "target_id", "task", "config", "forced_top1",
            name="uq_mapping_source_target_task_config_forced"
        ),
        Index("ix_mapping_source_config", "source_id", "config"),
        Index("ix_mapping_task_config", "task", "config"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String)
    source_text = Column(Text)
    target_id = Column(String)
    target_label = Column(String)
    target_type = Column(String)
    s_sem = Column(Float)
    s_gr = Column(Float)
    s_con = Column(Float)
    s_final = Column(Float)
    forced_top1 = Column(Boolean)
    task = Column(String)
    config = Column(String)

class KGNode(Base):
    __tablename__ = "kg_nodes"
    id = Column(String, primary_key=True)
    label = Column(String)
    node_type = Column(String)
    description = Column(Text)
    extra = Column(Text)

class KGEdge(Base):
    __tablename__ = "kg_edges"
    __table_args__ = (
        UniqueConstraint(
            "source_id", "target_id", "edge_type", "weight", "config",
            name="uq_edge_source_target_type_weight_config"
        ),
        Index("ix_edge_source", "source_id"),
        Index("ix_edge_target", "target_id"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String)
    target_id = Column(String)
    edge_type = Column(String)
    weight = Column(Float)
    config = Column(String)

class CRIByRanah(Base):
    __tablename__ = "cri_by_ranah"
    ranah = Column(String, primary_key=True)
    n_items = Column(Integer)
    has_mapping_esco = Column(Float)
    has_mapping_onet = Column(Float)
    has_mapping_skkni = Column(Float)
    mean_sfinal_esco = Column(Float)
    mean_sfinal_onet = Column(Float)
    mean_sfinal_skkni = Column(Float)

class DomainFilterResult(Base):
    __tablename__ = "domain_filter_results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    prodi = Column(String)         # 'SI', 'TI', 'CS', 'SE', 'CE', 'DS'
    node_id = Column(String)       # ESCO skill URI
    s_con = Column(Float)          # 1.0 | 0.5 | 0.0
    domain_status = Column(String) # 'core' | 'adjacent' | 'outside'
    config = Column(String)        # config versi yang dijalankan
    sim_score = Column(Float, default=0.0)  # raw cosine similarity score
