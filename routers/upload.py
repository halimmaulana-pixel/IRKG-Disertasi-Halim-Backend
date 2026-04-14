# backend/routers/upload.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import CPLItem, CRIResult, KGNode
from pydantic import BaseModel
from typing import List
import services.pipeline_runner as pipeline_runner

router = APIRouter()


class CPLInput(BaseModel):
    items: List[dict]
    prodi_name: str
    prodi_code: str


class CPLRunRequest(BaseModel):
    prodi_code: str
    config: str = "v1.2"


@router.post("/cpl")
def upload_cpl(payload: CPLInput, db: Session = Depends(get_db)):
    """Simpan CPL baru ke database"""
    stored = []
    for i, item in enumerate(payload.items):
        cpl_id = f"{payload.prodi_code}_PLO-{i+1}"
        deskripsi = item.get("deskripsi") or item.get("deskripsi_cpl")
        if not deskripsi:
            raise HTTPException(400, f"Item ke-{i+1} harus punya field 'deskripsi'")

        cpl = CPLItem(
            id=cpl_id,
            prodi=payload.prodi_code,
            ranah=item.get("ranah", "Keterampilan Khusus"),
            deskripsi=deskripsi,
            bridged_text="",
            is_custom=True,
        )
        node = KGNode(
            id=cpl_id,
            label=cpl_id,
            node_type="CPL",
            description=deskripsi[:300],
            extra="{}",
        )
        db.merge(cpl)
        db.merge(node)
        stored.append(cpl_id)

    db.commit()
    return {
        "status": "stored",
        "prodi_code": payload.prodi_code,
        "n_items": len(stored),
        "item_ids": stored,
    }


@router.post("/run")
def run_pipeline_for_new_cpl(req: CPLRunRequest, db: Session = Depends(get_db)):
    """Jalankan pipeline untuk CPL yang sudah di-upload."""
    custom_cpls = db.query(CPLItem).filter(
        CPLItem.prodi == req.prodi_code,
        CPLItem.is_custom == True,
    ).all()

    if not custom_cpls:
        raise HTTPException(404, f"Tidak ada CPL untuk prodi {req.prodi_code}")

    if pipeline_runner.is_readonly_mode():
        raise HTTPException(
            409,
            "Webapp sedang dalam mode readonly (hasil riset final). "
            "Pipeline baru untuk CPL upload dinonaktifkan agar baseline riset tidak berubah.",
        )

    job = pipeline_runner.start_pipeline_job(mode="all")
    return {
        "status": "queued",
        "prodi_code": req.prodi_code,
        "n_cpl": len(custom_cpls),
        "message": "Pipeline dijalankan. Pantau status via pipeline endpoint.",
        "job_id": job["job_id"],
        "poll_endpoint": f"/api/pipeline/status/{job['job_id']}",
    }


@router.get("/status/{prodi_code}")
def get_run_status(prodi_code: str, db: Session = Depends(get_db)):
    cri_results = db.query(CRIResult).filter(
        CRIResult.prodi == prodi_code
    ).all()

    if not cri_results:
        return {"status": "pending", "prodi_code": prodi_code}

    return {
        "status": "done",
        "prodi_code": prodi_code,
        "n_results": len(cri_results),
    }

