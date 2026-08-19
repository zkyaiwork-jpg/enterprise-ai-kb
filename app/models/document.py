from datetime import datetime, timezone
from enum import Enum as PythonEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.user import User
    from app.models.team import Team


class DocumentVisibility(str, PythonEnum):
    PRIVATE = "private"
    TEAM = "team"
    DEPARTMENT = "department"
    COMPANY = "company"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    uploader_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True
    )
    visibility: Mapped[DocumentVisibility] = mapped_column(
        Enum(
            DocumentVisibility,
            values_callable=lambda enum_class: [item.value for item in enum_class],
            native_enum=False,
            create_constraint=True,
            name="document_visibility",
        ),
        default=DocumentVisibility.PRIVATE,
        nullable=False,
        index=True,
    )
    created_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    uploader: Mapped["User"] = relationship(back_populates="documents")
    department: Mapped["Department | None"] = relationship(back_populates="documents")
    team: Mapped["Team | None"] = relationship(back_populates="documents")
