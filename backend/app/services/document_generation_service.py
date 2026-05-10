from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.code_chunk import CodeChunk
from app.models.commit import Commit
from app.models.document import Document
from app.models.repository_file import RepositoryFile
from app.schemas.document_schema import DocumentGenerateRequest, DocumentType
from app.services.project_service import ProjectNotFoundError, get_project


class DocumentGenerationError(Exception):
    pass


INSUFFICIENT_DATA_MESSAGE = (
    "No code chunks found. Run Prepare Docs before document generation."
)
DOCUMENT_TITLES: dict[str, str] = {
    "overview": "Project Overview",
    "folder_structure": "Folder Structure",
    "api_documentation": "API Documentation",
    "onboarding_guide": "Onboarding Guide",
}


def generate_documents(db: Session, project_id: str, payload: DocumentGenerateRequest) -> list[Document]:
    try:
        project = get_project(db, project_id)
    except ProjectNotFoundError:
        raise

    repository_files = list(
        db.scalars(
            select(RepositoryFile)
            .where(RepositoryFile.project_id == project_id)
            .order_by(RepositoryFile.file_path)
            .limit(200),
        ).all(),
    )
    code_chunks = list(
        db.scalars(
            select(CodeChunk)
            .options(selectinload(CodeChunk.file))
            .where(CodeChunk.project_id == project_id)
            .order_by(CodeChunk.file_id, CodeChunk.chunk_index)
            .limit(80),
        ).all(),
    )

    if not repository_files:
        raise DocumentGenerationError(
            "No scanned files found. Run repository scan before document generation.",
        )

    if not code_chunks:
        raise DocumentGenerationError(INSUFFICIENT_DATA_MESSAGE)

    commit = _find_commit(db, project_id, project.last_commit_hash)
    generated_documents: list[Document] = []

    db.execute(
        delete(Document).where(
            Document.project_id == project_id,
            Document.language == payload.language,
            Document.document_type.in_(payload.document_types),
        ),
    )

    for document_type in payload.document_types:
        content = _generate_markdown_document(
            project_name=project.name,
            repository_url=project.repository_url,
            document_type=document_type,
            language=payload.language,
            repository_files=repository_files,
            code_chunks=code_chunks,
        )
        document = Document(
            project_id=project_id,
            file_id=None,
            generated_from_commit_id=commit.id if commit else None,
            generated_from_commit_hash=project.last_commit_hash,
            document_type=document_type,
            title=DOCUMENT_TITLES[document_type],
            content=_ensure_document_content(content, document_type, payload.language),
            language=payload.language,
        )
        db.add(document)
        generated_documents.append(document)

    db.commit()

    for document in generated_documents:
        db.refresh(document)

    return generated_documents


def list_documents(db: Session, project_id: str) -> list[Document]:
    get_project(db, project_id)
    return list(
        db.scalars(
            select(Document)
            .where(Document.project_id == project_id)
            .order_by(Document.document_type, Document.language),
        ).all(),
    )


def get_document(db: Session, project_id: str, document_id: str) -> Document:
    get_project(db, project_id)
    document = db.scalar(
        select(Document).where(Document.project_id == project_id, Document.id == document_id),
    )

    if document is None:
        raise DocumentGenerationError(
            f"Document not found for this project. project_id={project_id}, document_id={document_id}",
        )

    if not document.content.strip():
        document.content = _build_document_fallback_content(
            title=document.title,
            document_type=document.document_type,
            language=document.language,
        )
        db.commit()
        db.refresh(document)

    return document


def _find_commit(db: Session, project_id: str, commit_hash: str | None) -> Commit | None:
    if not commit_hash:
        return None

    return db.scalar(
        select(Commit).where(
            Commit.project_id == project_id,
            Commit.commit_hash == commit_hash,
        ),
    )


def _ensure_document_content(content: str | None, document_type: DocumentType, language: str) -> str:
    normalized = (content or "").strip()

    if normalized:
        return normalized

    return _build_document_fallback_content(DOCUMENT_TITLES[document_type], document_type, language)


def _build_document_fallback_content(title: str, document_type: str, language: str) -> str:
    if language == "ko":
        return (
            f"# {title}\n\n"
            "문서 내용이 비어 있어 기본 fallback 문서를 표시합니다.\n\n"
            f"- document_type: `{document_type}`\n"
            "- 문서를 다시 생성해 주세요.\n"
        )

    return (
        f"# {title}\n\n"
        "Document content was empty, so a fallback document is being shown.\n\n"
        f"- document_type: `{document_type}`\n"
        "- Please regenerate the document.\n"
    )


def _generate_markdown_document(
    project_name: str,
    repository_url: str,
    document_type: DocumentType,
    language: str,
    repository_files: list[RepositoryFile],
    code_chunks: list[CodeChunk],
) -> str:
    if not settings.openai_api_key:
        return _generate_local_markdown_document(
            project_name=project_name,
            repository_url=repository_url,
            document_type=document_type,
            language=language,
            repository_files=repository_files,
            code_chunks=code_chunks,
        )

    from openai import OpenAI

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        context = _build_document_context(repository_files, code_chunks)
        language_instruction = "Write in Korean." if language == "ko" else "Write in English."
        response = client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You generate markdown documentation from analyzed repository files and "
                        "code chunks. Use only the provided context. If the context is insufficient, "
                        f"return exactly: {INSUFFICIENT_DATA_MESSAGE}. "
                        f"{language_instruction}"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Project: {project_name}\n"
                        f"Repository URL: {repository_url}\n"
                        f"Document type: {document_type}\n\n"
                        f"Context:\n{context}"
                    ),
                },
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content

        if content:
            return content
    except Exception:
        pass

    return _generate_local_markdown_document(
        project_name=project_name,
        repository_url=repository_url,
        document_type=document_type,
        language=language,
        repository_files=repository_files,
        code_chunks=code_chunks,
    )


def _generate_local_markdown_document(
    project_name: str,
    repository_url: str,
    document_type: DocumentType,
    language: str,
    repository_files: list[RepositoryFile],
    code_chunks: list[CodeChunk],
) -> str:
    heading = DOCUMENT_TITLES[document_type]
    file_lines = [
        f"- `{file.file_path}` ({file.language or 'unknown'}, {file.size_bytes} bytes)"
        for file in repository_files[:30]
    ]
    chunk_lines = [
        "\n".join(
            [
                f"### {chunk.file.file_path}:{chunk.start_line}-{chunk.end_line}",
                "```",
                chunk.content[:1200],
                "```",
            ],
        )
        for chunk in code_chunks[:8]
    ]

    if language == "ko":
        return "\n\n".join(
            [
                f"# {heading}",
                f"프로젝트: **{project_name}**",
                f"저장소: {repository_url}",
                "OpenAI API 키가 없어 로컬 분석 데이터만 사용해 문서를 생성했습니다.",
                "## 스캔된 파일",
                "\n".join(file_lines),
                "## 주요 코드 청크",
                "\n\n".join(chunk_lines),
            ],
        )

    return "\n\n".join(
        [
            f"# {heading}",
            f"Project: **{project_name}**",
            f"Repository: {repository_url}",
            "OpenAI API key is not configured, so this document was generated from local analysis data.",
            "## Scanned Files",
            "\n".join(file_lines),
            "## Representative Code Chunks",
            "\n\n".join(chunk_lines),
        ],
    )


def _build_document_context(
    repository_files: list[RepositoryFile],
    code_chunks: list[CodeChunk],
) -> str:
    file_lines = [
        f"- {file.file_path} ({file.language or 'unknown'}, {file.size_bytes} bytes)"
        for file in repository_files[:120]
    ]
    chunk_lines = [
        "\n".join(
            [
                f"File: {chunk.file.file_path}",
                f"Lines: {chunk.start_line}-{chunk.end_line}",
                f"Content:\n{chunk.content[:2000]}",
            ],
        )
        for chunk in code_chunks[:30]
    ]

    return "\n".join(
        [
            "Repository files:",
            *file_lines,
            "\nCode chunks:",
            "\n\n---\n\n".join(chunk_lines),
        ],
    )
