from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document_translation import DocumentTranslation
from app.schemas.document_schema import DocumentTranslateRequest
from app.services.document_generation_service import DocumentGenerationError, get_document
from app.services.project_service import ProjectNotFoundError


class DocumentTranslationError(Exception):
    pass


PRESERVED_TERMS = [
    "API",
    "controller",
    "service",
    "repository",
    "middleware",
    "endpoint",
    "request",
    "response",
    "payload",
    "schema",
    "DTO",
    "JWT",
    "token",
    "hook",
    "component",
    "router",
    "handler",
]


def translate_document(
    db: Session,
    project_id: str,
    document_id: str,
    payload: DocumentTranslateRequest,
) -> DocumentTranslation:
    try:
        document = get_document(db, project_id, document_id)
    except ProjectNotFoundError:
        raise
    except DocumentGenerationError as exc:
        raise DocumentTranslationError(str(exc)) from exc

    cached_translation = db.scalar(
        select(DocumentTranslation).where(
            DocumentTranslation.document_id == document_id,
            DocumentTranslation.language == payload.target_language,
            DocumentTranslation.preserve_terms == payload.preserve_terms,
            DocumentTranslation.translation_status == "completed",
        ),
    )

    if cached_translation is not None:
        return cached_translation

    translation = DocumentTranslation(
        document_id=document_id,
        language=payload.target_language,
        title=document.title,
        content="",
        translation_status="running",
        preserve_terms=payload.preserve_terms,
    )
    db.add(translation)
    db.commit()
    db.refresh(translation)

    try:
        translated_title, translated_content = _translate_markdown(
            title=document.title,
            content=document.content,
            target_language=payload.target_language,
            preserve_terms=payload.preserve_terms,
        )
        translation.title = translated_title
        translation.content = translated_content
        translation.translation_status = "completed"
        db.commit()
        db.refresh(translation)
        return translation
    except Exception as exc:
        db.rollback()
        translation = db.get(DocumentTranslation, translation.id)

        if translation is not None:
            translation.translation_status = "failed"
            translation.content = str(exc)
            db.commit()

        raise DocumentTranslationError(str(exc)) from exc


def list_document_translations(
    db: Session,
    project_id: str,
    document_id: str,
) -> list[DocumentTranslation]:
    try:
        get_document(db, project_id, document_id)
    except ProjectNotFoundError:
        raise
    except DocumentGenerationError as exc:
        raise DocumentTranslationError(str(exc)) from exc

    return list(
        db.scalars(
            select(DocumentTranslation)
            .where(DocumentTranslation.document_id == document_id)
            .order_by(DocumentTranslation.language, DocumentTranslation.created_at.desc()),
        ).all(),
    )


def _translate_markdown(
    title: str,
    content: str,
    target_language: str,
    preserve_terms: bool,
) -> tuple[str, str]:
    if not settings.openai_api_key:
        raise DocumentTranslationError("OPENAI_API_KEY is required to translate documents.")

    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    language_name = "Korean" if target_language == "ko" else "English"
    preserve_instruction = (
        "Preserve these technical terms exactly as written: "
        + ", ".join(PRESERVED_TERMS)
        if preserve_terms
        else "Translate naturally while keeping markdown valid."
    )
    response = client.chat.completions.create(
        model=settings.openai_chat_model,
        messages=[
            {
                "role": "system",
                "content": (
                    f"Translate markdown documentation to {language_name}. "
                    "Keep markdown formatting, headings, lists, code fences, links, and tables intact. "
                    f"{preserve_instruction}"
                ),
            },
            {
                "role": "user",
                "content": f"Title:\n{title}\n\nMarkdown:\n{content}",
            },
        ],
        temperature=0.1,
    )
    translated = response.choices[0].message.content

    if not translated:
        raise DocumentTranslationError("LLM returned an empty translation.")

    return title, translated
