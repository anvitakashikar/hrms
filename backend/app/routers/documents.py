from typing import Any, Dict, List

from fastapi import APIRouter, Depends, status

from app.dependencies.auth import get_current_user

router = APIRouter()

document_store: Dict[str, Dict[str, Any]] = {}


@router.post("", status_code=status.HTTP_201_CREATED)
def upload_document(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    doc_id = f"doc-{len(document_store) + 1}"
    item = {
        "id": doc_id,
        "org_id": current_user["org_id"],
        "name": payload["name"],
        "category": payload.get("category", "General"),
        "owner": payload.get("owner", current_user["email"]),
        "status": "uploaded",
    }
    document_store[doc_id] = item
    return item


@router.get("")
def list_documents(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return [item for item in document_store.values() if item["org_id"] == current_user["org_id"]]
