from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/docs", tags=["docs"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("")
async def upload_doc(file: UploadFile = File(...)):
    """上传测试文档"""
    try:
        # Generate safe filename or keep original
        # For simplicity MVP: use original filename but prevent overwrite collision?
        # Or simple prefix.
        
        # PRD says: doc_id
        file_ext = os.path.splitext(file.filename)[1]
        doc_id = f"{os.path.splitext(file.filename)[0]}_{str(uuid.uuid4())[:8]}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, doc_id)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {
            "doc_id": doc_id,
            "filename": file.filename,
            "path": file_path,
            "uploaded_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{doc_id}")
async def get_doc(doc_id: str):
    path = os.path.join(UPLOAD_DIR, doc_id)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Document not found")
    return {"doc_id": doc_id, "exists": True}
