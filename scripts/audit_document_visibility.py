"""Read-only report for unsafe or inconsistent document visibility metadata."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.database.database import SessionLocal
from app.models.document import Document, DocumentVisibility
from app.models.user import User
from app.services.document_service import list_documents


def main() -> int:
    chroma_documents = list_documents()
    chroma_metadata = {
        str(item.get("document_id")): item
        for item in chroma_documents
        if item.get("document_id") is not None
    }
    findings: list[tuple[str, str, str, str, str, str]] = []
    with SessionLocal() as database:
        documents = database.scalars(
            select(Document).options(joinedload(Document.uploader).joinedload(User.role))
        ).unique().all()
        for document in documents:
            role = document.uploader.role.name if document.uploader.role else "none"
            visibility = document.visibility.value
            if role == "employee" and document.visibility is not DocumentVisibility.PRIVATE:
                findings.append((str(document.id), document.filename, str(document.uploader_id), role, visibility, "employee_non_private"))
            if role == "leader" and document.visibility in {DocumentVisibility.DEPARTMENT, DocumentVisibility.COMPANY}:
                findings.append((str(document.id), document.filename, str(document.uploader_id), role, visibility, "leader_high_scope"))
            chroma = chroma_metadata.get(str(document.id), {})
            if chroma.get("visibility") != visibility:
                findings.append((str(document.id), document.filename, str(document.uploader_id), role, visibility, "sql_chroma_visibility_mismatch"))
            if document.visibility is DocumentVisibility.TEAM and document.team_id is None:
                findings.append((str(document.id), document.filename, str(document.uploader_id), role, visibility, "team_visibility_without_team"))
            if int(chroma.get("team_id") or 0) != int(document.team_id or 0):
                findings.append((str(document.id), document.filename, str(document.uploader_id), role, visibility, "sql_chroma_team_mismatch"))
            if document.team and document.team.department_id != document.department_id:
                findings.append((str(document.id), document.filename, str(document.uploader_id), role, visibility, "document_team_department_mismatch"))

        users = database.scalars(select(User).options(joinedload(User.team), joinedload(User.role))).all()
        for user in users:
            if user.team and user.team.department_id != user.department_id:
                findings.append(("-", "-", str(user.id), user.role.name if user.role else "none", "-", "user_team_department_mismatch"))

        print("document_id\tfilename\tuploader_id\trole\tvisibility\tissue_type")
        for finding in findings:
            print("\t".join(finding))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
