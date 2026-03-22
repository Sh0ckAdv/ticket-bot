from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class GuildSettings(Base):
    __tablename__ = "guild_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)

    tickets_category_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    logs_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    transcripts_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    password_support_role_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    discord_staff_role_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    manager_discord_role_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    max_open_tickets_per_user: Mapped[int] = mapped_column(Integer, default=1)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    panels: Mapped[list["TicketPanel"]] = relationship(
        back_populates="guild_settings",
        cascade="all, delete-orphan",
    )
    tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="guild_settings",
        cascade="all, delete-orphan",
    )


class TicketPanel(Base):
    __tablename__ = "ticket_panels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("guild_settings.guild_id", ondelete="CASCADE"),
        index=True,
    )

    channel_id: Mapped[int] = mapped_column(BigInteger)
    message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    title: Mapped[str] = mapped_column(String(150), default="Centrul de Suport")
    description: Mapped[str] = mapped_column(
        Text,
        default="Alege categoria care se potrivește cel mai bine problemei tale.",
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    guild_settings: Mapped["GuildSettings"] = relationship(back_populates="panels")


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    guild_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("guild_settings.guild_id", ondelete="CASCADE"),
        index=True,
    )
    channel_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    creator_id: Mapped[int] = mapped_column(BigInteger, index=True)

    ticket_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="open")

    claimed_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    closed_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    renamed_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    guild_settings: Mapped["GuildSettings"] = relationship(back_populates="tickets")
    logs: Mapped[list["TicketLog"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
    )


class TicketBlacklist(Base):
    __tablename__ = "ticket_blacklist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)

    reason: Mapped[str] = mapped_column(String(255), default="Niciun motiv specificat.")
    added_by: Mapped[int] = mapped_column(BigInteger)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TicketLog(Base):
    __tablename__ = "ticket_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tickets.id", ondelete="CASCADE"),
        index=True,
    )

    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    action: Mapped[str] = mapped_column(String(50))
    actor_id: Mapped[int] = mapped_column(BigInteger)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    ticket: Mapped["Ticket"] = relationship(back_populates="logs")

class StaffPoint(Base):
    __tablename__ = "staff_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    points: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

class StaffPointReset(Base):
    __tablename__ = "staff_point_resets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    last_reset_key: Mapped[str] = mapped_column(String(7))  # ex: 2026-03

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )