from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.document import Document
    from app.models.user import User


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (
        UniqueConstraint("department_id", "name", name="uq_teams_department_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    department: Mapped["Department"] = relationship(back_populates="teams")
    users: Mapped[list["User"]] = relationship(
        back_populates="team",
        passive_deletes=True,
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="team",
        passive_deletes=True,
    )
