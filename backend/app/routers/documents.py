import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse

from app.database import get_store
from app.dependencies.auth import get_current_user, require_roles
from app.services.notification_service import notify_reviewers, notify_user


router = APIRouter()

store = get_store()

MANAGERS = ("admin", "hr")
DOCUMENT_PERMISSION_ROLES = ("admin", "hr", "manager", "employee")

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".doc",
    ".docx",
}

MAX_DOCUMENT_BYTES = 10 * 1024 * 1024

UPLOAD_ROOT = (
    Path(__file__).resolve().parents[2] / "private_uploads"
)


def _require_org(current_user: Dict[str, Any]) -> str:
    org_id = current_user.get("org_id")

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Complete organization setup first",
        )

    return org_id


def _can_manage(user: Dict[str, Any]) -> bool:
    return user.get("role") in MANAGERS


def _can_access_document(
    document: Dict[str, Any],
    current_user: Dict[str, Any],
) -> bool:
    """
    Check whether the current user can access a document.

    Access is granted when:
    - The user is an admin or HR user.
    - The user owns the document.
    - The user has an explicit user permission.
    - The user's role has been granted permission.
    """

    if _can_manage(current_user):
        return True

    if document.get("owner_user_id") == current_user.get("id"):
        return True

    permissions = document.get("access_permissions", [])

    for permission in permissions:
        if permission.get("user_id") == current_user.get("id"):
            return True

        if (
            permission.get("role") == current_user.get("role")
            and permission.get("role") in DOCUMENT_PERMISSION_ROLES
        ):
            return True

    return False


def _accessible_documents(
    current_user: Dict[str, Any],
) -> List[Dict[str, Any]]:
    documents = store.list_module_records(
        "employee_documents",
        _require_org(current_user),
    )

    return [
        document
        for document in documents
        if _can_access_document(document, current_user)
    ]


def _owned_documents(
    current_user: Dict[str, Any],
) -> List[Dict[str, Any]]:
    items = store.list_module_records(
        "employee_documents",
        _require_org(current_user),
    )

    if _can_manage(current_user):
        return items

    return [
        item
        for item in items
        if item.get("owner_user_id") == current_user["id"]
    ]


async def _save_upload(
    file: UploadFile,
    org_id: str,
    document_id: str,
) -> Dict[str, Any]:
    extension = Path(file.filename or "").suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="Unsupported document format",
        )

    content = await file.read(
        MAX_DOCUMENT_BYTES + 1
    )

    if not content:
        raise HTTPException(
            status_code=400,
            detail="The uploaded document is empty",
        )

    if len(content) > MAX_DOCUMENT_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Documents must be 10 MB or smaller",
        )

    directory = UPLOAD_ROOT / org_id
    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    storage_name = (
        f"{document_id}-{uuid.uuid4().hex}{extension}"
    )

    destination = directory / storage_name
    destination.write_bytes(content)

    return {
        "storage_path": str(destination),
        "file_name": Path(
            file.filename or storage_name
        ).name,
        "content_type": (
            file.content_type
            or "application/octet-stream"
        ),
        "size_bytes": len(content),
    }


@router.get("/categories")
def list_categories(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    org_id = _require_org(current_user)

    return store.list_module_records(
        "document_categories",
        org_id,
    )


@router.post(
    "/categories",
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(
        require_roles(*MANAGERS)
    ),
) -> Dict[str, Any]:
    org_id = _require_org(current_user)

    name = str(
        payload.get("name", "")
    ).strip()

    if not name:
        raise HTTPException(
            status_code=422,
            detail="Category name is required",
        )

    existing_categories = store.list_module_records(
        "document_categories",
        org_id,
    )

    if any(
        item["name"].casefold() == name.casefold()
        for item in existing_categories
    ):
        raise HTTPException(
            status_code=409,
            detail="Document category already exists",
        )

    category = store.create_module_record(
        "document_categories",
        {
            "org_id": org_id,
            "name": name,
            "description": payload.get(
                "description",
                "",
            ),
            "required": bool(
                payload.get("required", False)
            ),
            "active": True,
            "created_by": current_user["id"],
        },
    )

    store.add_audit_log(
        current_user["id"],
        org_id,
        "document_category.created",
        {
            "record_id": category["id"],
        },
    )

    return category


@router.patch("/categories/{category_id}")
def update_category(
    category_id: str,
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(
        require_roles(*MANAGERS)
    ),
) -> Dict[str, Any]:
    org_id = _require_org(current_user)

    allowed = {
        key: payload[key]
        for key in (
            "name",
            "description",
            "required",
            "active",
        )
        if key in payload
    }

    category = store.update_module_record(
        "document_categories",
        category_id,
        org_id,
        allowed,
    )

    if category is None:
        raise HTTPException(
            status_code=404,
            detail="Document category not found",
        )

    store.add_audit_log(
        current_user["id"],
        org_id,
        "document_category.updated",
        {
            "record_id": category_id,
            "changes": allowed,
        },
    )

    return category


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    request: Request,
    current_user: Dict[str, Any] = Depends(
        get_current_user
    ),
) -> Dict[str, Any]:
    org_id = _require_org(current_user)

    content_type = request.headers.get(
        "content-type",
        "",
    )

    upload: Optional[UploadFile] = None

    metadata: Dict[str, Any] = {}

    if content_type.startswith(
        "multipart/form-data"
    ):
        form = await request.form()

        candidate = form.get("file")

        if (
            not candidate
            or not getattr(
                candidate,
                "filename",
                None,
            )
        ):
            raise HTTPException(
                status_code=422,
                detail="A document file is required",
            )

        upload = candidate

        category_id = str(
            form.get("category_id", "")
        )

        expiry_date = (
            str(form.get("expiry_date") or "")
            or None
        )

        notes = str(
            form.get("notes", "")
        )

        name = upload.filename

        category_name = None

    else:
        metadata = await request.json()

        name = str(
            metadata.get("name", "")
        ).strip()

        if not name:
            raise HTTPException(
                status_code=422,
                detail="Document name is required",
            )

        category_name = (
            str(
                metadata.get(
                    "category",
                    "General",
                )
            ).strip()
            or "General"
        )

        categories = store.list_module_records(
            "document_categories",
            org_id,
        )

        category = next(
            (
                item
                for item in categories
                if item["name"].casefold()
                == category_name.casefold()
            ),
            None,
        )

        if category is None:
            category = store.create_module_record(
                "document_categories",
                {
                    "org_id": org_id,
                    "name": category_name,
                    "description": (
                        "Legacy metadata category"
                    ),
                    "required": False,
                    "active": True,
                    "created_by": current_user["id"],
                },
            )

        category_id = category["id"]

        expiry_date = metadata.get(
            "expiry_date"
        )

        notes = str(
            metadata.get("notes", "")
        )

    category = store.get_module_record(
        "document_categories",
        category_id,
        org_id,
    )

    if (
        category is None
        or not category.get("active", True)
    ):
        raise HTTPException(
            status_code=422,
            detail="Select an active document category",
        )

    if expiry_date:
        try:
            datetime.strptime(
                expiry_date,
                "%Y-%m-%d",
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail="Expiry date must use YYYY-MM-DD",
            ) from exc

    document_id = str(uuid.uuid4())

    if upload:
        file_info = await _save_upload(
            upload,
            org_id,
            document_id,
        )
    else:
        file_info = {
            "storage_path": None,
            "file_name": name,
            "content_type": "application/json",
            "size_bytes": 0,
        }

    owner_user = current_user

    owner_email = (
        metadata.get("owner")
        if not upload
        and _can_manage(current_user)
        else None
    )

    if owner_email:
        candidate_user = store.get_user_by_email(
            owner_email
        )

        if (
            candidate_user
            and candidate_user.get("org_id")
            == org_id
        ):
            owner_user = candidate_user

    employee = store.get_employee_by_user_email(
        org_id,
        owner_user["email"],
    )

    item = store.create_module_record(
        "employee_documents",
        {
            "id": document_id,
            "org_id": org_id,
            "owner_user_id": owner_user["id"],
            "employee_id": (
                employee["id"]
                if employee
                else None
            ),
            "category_id": category_id,
            "category": category["name"],
            "name": file_info["file_name"],
            "file_name": file_info["file_name"],
            "content_type": file_info[
                "content_type"
            ],
            "size_bytes": file_info[
                "size_bytes"
            ],
            "storage_path": file_info[
                "storage_path"
            ],
            "expiry_date": expiry_date,
            "notes": notes.strip(),
            "status": (
                "pending_verification"
                if upload
                else "uploaded"
            ),
            "metadata_only": upload is None,
            "rejection_reason": None,
            "version": 1,
            "uploaded_at": datetime.utcnow().isoformat(),
            "access_permissions": [],
        },
    )

    store.add_audit_log(
        current_user["id"],
        org_id,
        "employee_document.uploaded",
        {
            "record_id": document_id,
        },
    )

    notify_reviewers(
        org_id,
        "document.pending_verification",
        "Document awaits verification",
        (
            f"{item['category']} was uploaded "
            "and needs review."
        ),
        "employee_document",
        document_id,
    )

    return {
        key: value
        for key, value in item.items()
        if key != "storage_path"
    }


@router.get("")
def list_documents(
    current_user: Dict[str, Any] = Depends(
        get_current_user
    ),
) -> List[Dict[str, Any]]:
    return [
        {
            key: value
            for key, value in item.items()
            if key != "storage_path"
        }
        for item in _owned_documents(current_user)
    ]


@router.get("/missing")
def missing_documents(
    current_user: Dict[str, Any] = Depends(
        get_current_user
    ),
) -> List[Dict[str, Any]]:
    org_id = _require_org(current_user)

    categories = [
        item
        for item in store.list_module_records(
            "document_categories",
            org_id,
        )
        if item.get("active")
        and item.get("required")
    ]

    documents = _owned_documents(current_user)

    owners = {
        item.get("owner_user_id")
        for item in documents
    }

    if _can_manage(current_user):
        owners = {
            user["id"]
            for user in store.users.values()
            if (
                user.get("org_id") == org_id
                and user.get("role") != "admin"
            )
        }

    return [
        {
            "owner_user_id": owner_id,
            "category_id": category["id"],
            "category": category["name"],
        }
        for owner_id in owners
        for category in categories
        if not any(
            doc.get("owner_user_id") == owner_id
            and doc.get("category_id")
            == category["id"]
            and doc.get("status") == "approved"
            for doc in documents
        )
    ]


@router.get("/{document_id}/download")
def download_document(
    document_id: str,
    current_user: Dict[str, Any] = Depends(
        get_current_user
    ),
) -> FileResponse:
    items = _owned_documents(current_user)

    item = next(
        (
            doc
            for doc in items
            if doc["id"] == document_id
        ),
        None,
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    storage_path = item.get("storage_path")

    if not storage_path:
        raise HTTPException(
            status_code=404,
            detail="Document file is unavailable",
        )

    path = Path(storage_path)

    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Document file is unavailable",
        )

    return FileResponse(
        path,
        media_type=item.get("content_type"),
        filename=item.get("file_name"),
    )


@router.patch("/{document_id}/verification")
def verify_document(
    document_id: str,
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(
        require_roles(*MANAGERS)
    ),
) -> Dict[str, Any]:
    org_id = _require_org(current_user)

    decision = payload.get("status")

    if decision not in {
        "approved",
        "rejected",
    }:
        raise HTTPException(
            status_code=422,
            detail=(
                "Status must be approved or rejected"
            ),
        )

    reason = str(
        payload.get(
            "rejection_reason",
            "",
        )
    ).strip()

    if decision == "rejected" and not reason:
        raise HTTPException(
            status_code=422,
            detail=(
                "A rejection reason is required"
            ),
        )

    document = store.get_module_record(
        "employee_documents",
        document_id,
        org_id,
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    if document.get("status") != "pending_verification":
        raise HTTPException(
            status_code=409,
            detail=(
                "Only pending documents can be reviewed"
            ),
        )

    updated = store.update_module_record(
        "employee_documents",
        document_id,
        org_id,
        {
            "status": decision,
            "rejection_reason": (
                reason
                if decision == "rejected"
                else None
            ),
            "verified_by": current_user["id"],
            "verified_at": (
                datetime.utcnow().isoformat()
            ),
        },
    )

    store.add_audit_log(
        current_user["id"],
        org_id,
        "employee_document.verified",
        {
            "record_id": document_id,
            "status": decision,
            "reason": reason,
        },
    )

    notify_user(
        org_id,
        document["owner_user_id"],
        f"document.{decision}",
        f"Document {decision}",
        (
            f"Your {document['category']} "
            f"document was {decision}."
        ),
        "employee_document",
        document_id,
    )

    return {
        key: value
        for key, value in updated.items()
        if key != "storage_path"
    }


@router.post(
    "/{document_id}/replace",
    status_code=status.HTTP_200_OK,
)
async def replace_rejected_document(
    document_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(
        get_current_user
    ),
) -> Dict[str, Any]:
    org_id = _require_org(current_user)

    document = store.get_module_record(
        "employee_documents",
        document_id,
        org_id,
    )

    if (
        document is None
        or (
            document.get("owner_user_id")
            != current_user["id"]
            and not _can_manage(current_user)
        )
    ):
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    if document.get("status") != "rejected":
        raise HTTPException(
            status_code=409,
            detail=(
                "Only rejected documents can be replaced"
            ),
        )

    form = await request.form()

    file = form.get("file")

    if (
        not file
        or not getattr(
            file,
            "filename",
            None,
        )
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "A replacement document file is required"
            ),
        )

    expiry_date = (
        str(form.get("expiry_date") or "")
        or None
    )

    notes = str(
        form.get("notes", "")
    )

    file_info = await _save_upload(
        file,
        org_id,
        document_id,
    )

    history = list(
        document.get("versions", [])
    )

    history.append(
        {
            "version": document["version"],
            "storage_path": document[
                "storage_path"
            ],
            "file_name": document[
                "file_name"
            ],
            "uploaded_at": document[
                "uploaded_at"
            ],
        }
    )

    updated = store.update_module_record(
        "employee_documents",
        document_id,
        org_id,
        {
            **file_info,
            "name": file_info["file_name"],
            "expiry_date": expiry_date,
            "notes": notes.strip(),
            "versions": history,
            "version": document["version"] + 1,
            "status": "pending_verification",
            "rejection_reason": None,
            "uploaded_at": (
                datetime.utcnow().isoformat()
            ),
            "verified_by": None,
            "verified_at": None,
        },
    )

    store.add_audit_log(
        current_user["id"],
        org_id,
        "employee_document.replaced",
        {
            "record_id": document_id,
            "version": updated["version"],
        },
    )

    return {
        key: value
        for key, value in updated.items()
        if key != "storage_path"
    }