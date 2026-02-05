"""
RESTful API endpoints for document upload, list, get, delete, and generated PDFs.
"""
import logging
import shutil
import time
from pathlib import Path
from typing import List
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.exceptions import DocumentNotFoundError, UnauthorizedError
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database.models import Document, GeneratedDocument
from backend.database.schemas import (
    DocumentRead,
    GeneratedDocumentRead,
    GeneratedDocumentWithPDF,
    DocumentGenerationResponse,
)
from backend.dependencies import get_db_session
from backend.auth.users import current_active_user
from backend.database.models import User
from backend.memory.embeddings import EmbeddingService
from backend.memory.utils import validate_case_ownership

from .processor import process_document
from .statement_of_claim import generate_statement_of_claim_pdf
from .hearing_script import generate_hearing_script_pdf
from .advice_generator import generate_advice_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["documents"])

# Magic bytes for file type validation (not just extension)
MAGIC_PDF = b"%PDF"
MAGIC_PNG = b"\x89PNG\r\n\x1a\n"
MAGIC_JPEG = b"\xff\xd8\xff"


def _read_magic(file_path: Path, num_bytes: int = 12) -> bytes:
    """Read first num_bytes from file for magic number check."""
    with open(file_path, "rb") as f:
        return f.read(num_bytes)


def _validate_file_magic(file_path: Path, expected_ext: str) -> bool:
    """Validate file content matches expected type by magic bytes."""
    ext = expected_ext.lower()
    try:
        magic = _read_magic(file_path)
    except OSError:
        return False
    if ext == "pdf":
        return magic.startswith(MAGIC_PDF)
    if ext == "png":
        return magic.startswith(MAGIC_PNG)
    if ext in ("jpg", "jpeg"):
        return magic.startswith(MAGIC_JPEG)
    return False


@router.post("/cases/{case_id}/documents/upload", response_model=DocumentRead, status_code=201)
async def upload_document(
    case_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
):
    """
    Upload a document for a case. Validates ownership, file type/size, extracts text,
    generates embedding, and creates a Document record with processed=False.
    """
    settings = get_settings()
    if not await validate_case_ownership(db, case_id, user.id):
        raise UnauthorizedError("Not authorized to add documents to this case.")

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    allowed = [e.lower().strip() for e in settings.ALLOWED_FILE_TYPES]
    if not allowed:
        allowed = ["pdf", "png", "jpg", "jpeg"]

    # Validate filename and extension
    if not file.filename or not file.filename.strip():
        raise HTTPException(status_code=400, detail="Missing filename")
    safe_name = file.filename.strip()
    if ".." in safe_name or "/" in safe_name or "\\" in safe_name:
        raise HTTPException(status_code=400, detail="Invalid filename")
    ext = Path(safe_name).suffix.lower().lstrip(".")
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(allowed)}",
        )

    # Save to temp file first to check size and magic bytes
    upload_dir = Path(settings.UPLOAD_DIR)
    case_dir = upload_dir / str(case_id)
    case_dir.mkdir(parents=True, exist_ok=True)
    temp_path = case_dir / f"_tmp_{uuid4()}{Path(safe_name).suffix}"

    try:
        try:
            with open(temp_path, "wb") as f:
                size = 0
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > max_bytes:
                        break
                    f.write(chunk)
        except OSError as e:
            logger.exception("Failed to save upload")
            raise HTTPException(status_code=500, detail="Failed to save file") from e

        if size > max_bytes:
            temp_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB} MB",
            )

        if not _validate_file_magic(temp_path, ext):
            temp_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="File content does not match declared type")

        # Final path with unique name
        unique_name = f"{uuid4()}{Path(safe_name).suffix}"
        final_path = case_dir / unique_name
        shutil.move(str(temp_path), str(final_path))
        file_path_str = str(final_path)

        # Extract text
        try:
            extracted_text = process_document(file_path_str, ext)
        except (ValueError, FileNotFoundError) as e:
            try:
                final_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            try:
                final_path.unlink(missing_ok=True)
            except OSError:
                pass
            logger.exception("Document processing failed")
            raise HTTPException(status_code=500, detail="Document processing failed") from e

        # Generate embedding if we have text
        embedding = None
        if extracted_text and extracted_text.strip():
            try:
                emb_svc = EmbeddingService()
                embedding = await emb_svc.generate_embedding(extracted_text)
            except Exception as e:
                logger.warning("Embedding generation failed for document: %s", e)
                # Continue without embedding; document still usable

        # Create Document record (relative path for portability)
        relative_path = f"{case_id}/{unique_name}"
        doc = Document(
            case_id=case_id,
            filename=safe_name,
            file_path=relative_path,
            file_type=ext,
            file_size=size,
            extracted_text=extracted_text or None,
            embedding=embedding,
            processed=False,
        )
        db.add(doc)
        await db.flush()
        await db.refresh(doc)
        return DocumentRead.model_validate(doc)

    except HTTPException:
        raise
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        if "final_path" in dir() and final_path.exists():
            final_path.unlink(missing_ok=True)
        logger.exception("Upload failed")
        raise HTTPException(status_code=500, detail="Upload failed") from e


@router.get("/cases/{case_id}/documents", response_model=List[DocumentRead])
async def list_documents(
    case_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
):
    """List all documents for a case. User must own the case."""
    if not await validate_case_ownership(db, case_id, user.id):
        raise UnauthorizedError("Not authorized to access this case.")
    result = await db.execute(select(Document).where(Document.case_id == case_id).order_by(Document.uploaded_at.desc()))
    documents = result.scalars().all()
    return [DocumentRead.model_validate(d) for d in documents]


@router.get("/documents/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
):
    """Retrieve a single document. User must own the case."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not await validate_case_ownership(db, doc.case_id, user.id):
        raise UnauthorizedError("Not authorized to access this document.")
    return DocumentRead.model_validate(doc)


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
):
    """Download an uploaded document file. User must own the case."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise DocumentNotFoundError("Document not found.", document_id=str(document_id))
    if not await validate_case_ownership(db, doc.case_id, user.id):
        raise UnauthorizedError("Not authorized to access this document.")

    upload_dir = Path(get_settings().UPLOAD_DIR)
    full_path = upload_dir / doc.file_path
    if not full_path.exists():
        logger.warning("Uploaded file missing: %s", full_path)
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(full_path),
        filename=doc.filename,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'},
    )


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> None:
    """Delete document record and file from disk. User must own the case."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not await validate_case_ownership(db, doc.case_id, user.id):
        raise HTTPException(status_code=403, detail="Not authorized to delete this document")

    # Remove file from disk (path stored as relative: case_id/filename)
    upload_dir = Path(get_settings().UPLOAD_DIR)
    file_path = upload_dir / doc.file_path
    try:
        if file_path.exists():
            file_path.unlink()
    except OSError as e:
        logger.warning("Could not delete file %s: %s", file_path, e)

    await db.delete(doc)
    await db.flush()


# --- Generated document PDF endpoints ---

_GENERATORS = {
    "statement_of_claim": generate_statement_of_claim_pdf,
    "hearing_script": generate_hearing_script_pdf,
    "legal_advice": generate_advice_pdf,
}


@router.post("/generated/{document_id}/generate-pdf", response_model=DocumentGenerationResponse)
async def generate_document_pdf(
    document_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
):
    """Generate PDF for a generated document. Updates file_path and returns document."""
    result = await db.execute(
        select(GeneratedDocument).where(GeneratedDocument.id == document_id)
    )
    gen_doc = result.scalar_one_or_none()
    if not gen_doc:
        raise DocumentNotFoundError("Generated document not found.", document_id=str(document_id))
    if not await validate_case_ownership(db, gen_doc.case_id, user.id):
        raise UnauthorizedError("Not authorized to access this document.")

    generator = _GENERATORS.get(gen_doc.document_type)
    if not generator:
        raise HTTPException(
            status_code=400,
            detail=f"PDF generation not supported for document type: {gen_doc.document_type}",
        )

    settings = get_settings()
    base_dir = Path(settings.GENERATED_DOCS_DIR)
    case_dir = base_dir / str(gen_doc.case_id)
    case_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{gen_doc.document_type}_{gen_doc.id}.pdf"
    output_path = case_dir / filename

    start = time.perf_counter()
    try:
        generator(gen_doc, str(output_path))
    except Exception as e:
        logger.exception("PDF generation failed for document %s: %s", document_id, e)
        raise HTTPException(
            status_code=500,
            detail="PDF generation failed",
        ) from e
    generation_time_ms = int((time.perf_counter() - start) * 1000)

    # Store path relative to GENERATED_DOCS_DIR for portability
    relative_path = f"{gen_doc.case_id}/{filename}"
    gen_doc.file_path = relative_path
    await db.flush()
    await db.refresh(gen_doc)

    base = GeneratedDocumentRead.model_validate(gen_doc)
    return DocumentGenerationResponse(
        **base.model_dump(),
        pdf_generated=True,
        generation_time_ms=generation_time_ms,
    )


@router.get("/generated/{document_id}/download")
async def download_generated_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
):
    """Download PDF for a generated document. Returns file or 404."""
    result = await db.execute(
        select(GeneratedDocument).where(GeneratedDocument.id == document_id)
    )
    gen_doc = result.scalar_one_or_none()
    if not gen_doc:
        raise DocumentNotFoundError("Generated document not found.", document_id=str(document_id))
    if not await validate_case_ownership(db, gen_doc.case_id, user.id):
        raise UnauthorizedError("Not authorized to access this document.")
    if not gen_doc.file_path:
        raise HTTPException(
            status_code=404,
            detail="PDF not generated yet. Call generate-pdf first.",
        )

    full_path = Path(get_settings().GENERATED_DOCS_DIR) / gen_doc.file_path
    if not full_path.exists():
        logger.warning("Generated PDF file missing: %s", full_path)
        raise HTTPException(status_code=404, detail="PDF file not found")

    return FileResponse(
        path=str(full_path),
        filename=full_path.name,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{full_path.name}"'},
    )


@router.get("/cases/{case_id}/generated", response_model=List[GeneratedDocumentWithPDF])
async def list_generated_documents(
    case_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
):
    """List all generated documents for a case, ordered by generated_at desc."""
    if not await validate_case_ownership(db, case_id, user.id):
        raise UnauthorizedError("Not authorized to access this case.")
    result = await db.execute(
        select(GeneratedDocument)
        .where(GeneratedDocument.case_id == case_id)
        .order_by(GeneratedDocument.generated_at.desc())
    )
    docs = result.scalars().all()
    return [GeneratedDocumentWithPDF.model_validate(d) for d in docs]


@router.post("/generated/{document_id}/regenerate", response_model=GeneratedDocumentRead)
async def regenerate_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
):
    """Create a new version of the generated document and generate its PDF. Fails atomically if PDF generation fails."""
    result = await db.execute(
        select(GeneratedDocument).where(GeneratedDocument.id == document_id)
    )
    existing = result.scalar_one_or_none()
    if not existing:
        raise DocumentNotFoundError("Generated document not found.", document_id=str(document_id))
    if not await validate_case_ownership(db, existing.case_id, user.id):
        raise UnauthorizedError("Not authorized to access this document.")

    generator = _GENERATORS.get(existing.document_type)
    if not generator:
        raise HTTPException(
            status_code=400,
            detail=f"PDF generation not supported for document type: {existing.document_type}",
        )

    new_version = existing.version + 1
    new_doc = GeneratedDocument(
        case_id=existing.case_id,
        document_type=existing.document_type,
        content=existing.content,
        file_path=None,
        version=new_version,
    )
    db.add(new_doc)
    await db.flush()
    await db.refresh(new_doc)

    settings = get_settings()
    base_dir = Path(settings.GENERATED_DOCS_DIR)
    case_dir = base_dir / str(new_doc.case_id)
    case_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{new_doc.document_type}_{new_doc.id}.pdf"
    output_path = case_dir / filename

    try:
        generator(new_doc, str(output_path))
    except Exception as e:
        logger.exception("PDF generation failed for document %s: %s", document_id, e)
        raise HTTPException(
            status_code=500,
            detail="PDF generation failed",
        ) from e

    relative_path = f"{new_doc.case_id}/{filename}"
    new_doc.file_path = relative_path
    await db.flush()
    await db.refresh(new_doc)

    return GeneratedDocumentRead.model_validate(new_doc)


@router.delete("/generated/{document_id}", status_code=204)
async def delete_generated_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> None:
    """Delete generated document record and its PDF file if present."""
    result = await db.execute(
        select(GeneratedDocument).where(GeneratedDocument.id == document_id)
    )
    gen_doc = result.scalar_one_or_none()
    if not gen_doc:
        raise DocumentNotFoundError("Generated document not found.", document_id=str(document_id))
    if not await validate_case_ownership(db, gen_doc.case_id, user.id):
        raise UnauthorizedError("Not authorized to delete this document.")

    if gen_doc.file_path:
        full_path = Path(get_settings().GENERATED_DOCS_DIR) / gen_doc.file_path
        try:
            if full_path.exists():
                full_path.unlink()
        except OSError as e:
            logger.warning("Could not delete generated PDF %s: %s", full_path, e)

    await db.delete(gen_doc)
    await db.flush()
