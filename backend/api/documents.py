import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import get_client_ip, require_role
from backend.models.document import Document, DocumentEntityType, DocumentType
from backend.models.user import User
from backend.schemas.common import PaginatedResponse
from backend.schemas.payment import (
    DocumentConfirmRequest,
    DocumentResponse,
    PresignedUrlRequest,
    PresignedUrlResponse,
)
from backend.services.audit_service import AuditService
from backend.services.minio_service import generate_presigned_put_url, get_public_file_url

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/presigned-url", response_model=PresignedUrlResponse)
async def get_presigned_url(
    body: PresignedUrlRequest,
    current_user: User = Depends(require_role("manager", "sb", "director")),
) -> PresignedUrlResponse:
    try:
        upload_url, object_key = generate_presigned_put_url(
            entity_type=body.entity_type,
            entity_id=str(body.entity_id),
            doc_type=body.doc_type,
            file_name=body.file_name,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"MinIO error: {exc}") from exc

    return PresignedUrlResponse(upload_url=upload_url, object_key=object_key)


@router.post("/confirm", response_model=DocumentResponse)
async def confirm_upload(
    body: DocumentConfirmRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "sb", "director")),
) -> DocumentResponse:
    try:
        entity_type = DocumentEntityType(body.entity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid entity_type: {body.entity_type}")

    try:
        doc_type = DocumentType(body.doc_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid doc_type: {body.doc_type}")

    file_url = get_public_file_url(body.object_key)

    document = Document(
        entity_type=entity_type,
        entity_id=body.entity_id,
        file_url=file_url,
        doc_type=doc_type,
        uploaded_by=current_user.id,
        file_name=body.file_name,
        file_size=body.file_size,
    )
    db.add(document)
    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="DOCUMENT_UPLOADED",
        entity="documents",
        entity_id=str(document.id) if document.id else None,
        new_val={
            "entity_type": body.entity_type,
            "entity_id": str(body.entity_id),
            "doc_type": body.doc_type,
            "file_name": body.file_name,
        },
        ip=get_client_ip(request),
    )
    await db.commit()
    await db.refresh(document)
    return DocumentResponse.model_validate(document)


@router.get("", response_model=PaginatedResponse[DocumentResponse])
async def list_documents(
    entity_type: str = Query(...),
    entity_id: uuid.UUID = Query(...),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "sb", "director")),
) -> PaginatedResponse[DocumentResponse]:
    from sqlalchemy import func

    try:
        et = DocumentEntityType(entity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid entity_type: {entity_type}")

    total = (
        await db.execute(
            select(func.count())
            .where(Document.entity_type == et)
            .where(Document.entity_id == entity_id)
        )
    ).scalar_one()

    rows = await db.execute(
        select(Document)
        .where(Document.entity_type == et)
        .where(Document.entity_id == entity_id)
        .order_by(Document.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    docs = rows.scalars().all()
    return PaginatedResponse(
        items=[DocumentResponse.model_validate(d) for d in docs],
        total=total,
        limit=limit,
        offset=offset,
    )
