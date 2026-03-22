from __future__ import annotations

from datetime import datetime, timezone
from calendar import month_name

import discord
from sqlalchemy import select

from bot.db.models import GuildSettings, StaffPoint, StaffPointReset
from bot.db.session import AsyncSessionLocal


def get_current_month_key() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.year:04d}-{now.month:02d}"


def get_previous_month_label() -> str:
    now = datetime.now(timezone.utc)
    year = now.year
    month = now.month - 1

    if month == 0:
        month = 12
        year -= 1

    return f"{month_name[month]} {year}"


async def process_monthly_staff_points_reset(bot: discord.Client) -> None:
    current_reset_key = get_current_month_key()
    previous_month_label = get_previous_month_label()

    async with AsyncSessionLocal() as session:
        settings_result = await session.execute(select(GuildSettings))
        all_settings = settings_result.scalars().all()

        for settings in all_settings:
            reset_result = await session.execute(
                select(StaffPointReset).where(StaffPointReset.guild_id == settings.guild_id)
            )
            reset_state = reset_result.scalar_one_or_none()

            if reset_state is not None and reset_state.last_reset_key == current_reset_key:
                continue

            guild = bot.get_guild(settings.guild_id)
            if guild is None:
                continue

            logs_channel = guild.get_channel(settings.logs_channel_id)
            if logs_channel is None or not isinstance(logs_channel, discord.TextChannel):
                continue

            points_result = await session.execute(
                select(StaffPoint)
                .where(StaffPoint.guild_id == guild.id)
                .order_by(StaffPoint.points.desc(), StaffPoint.user_id)
            )
            leaderboard = points_result.scalars().all()

            if leaderboard:
                embed = discord.Embed(
                    title="Leaderboard lunar tickete",
                    description=f"Clasamentul final pentru **{previous_month_label}**.",
                    color=discord.Color.gold(),
                    timestamp=datetime.now(timezone.utc),
                )

                lines = []
                for index, entry in enumerate(leaderboard[:10], start=1):
                    member = guild.get_member(entry.user_id)
                    name = member.mention if member else f"`{entry.user_id}`"
                    lines.append(f"**#{index}** • {name} — **{entry.points}** puncte")

                embed.add_field(
                    name="Top 10 Staff",
                    value="\n".join(lines),
                    inline=False,
                )
                embed.set_footer(text="Ratonii Tickets • Reset lunar puncte")

                await logs_channel.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="Reset lunar tickete",
                    description=(
                        f"Nu au existat puncte staff de resetat pentru **{previous_month_label}**."
                    ),
                    color=discord.Color.orange(),
                    timestamp=datetime.now(timezone.utc),
                )
                embed.set_footer(text="Ratonii Tickets • Reset lunar puncte")

                await logs_channel.send(embed=embed)

            for entry in leaderboard:
                entry.points = 0

            if reset_state is None:
                reset_state = StaffPointReset(
                    guild_id=guild.id,
                    last_reset_key=current_reset_key,
                )
                session.add(reset_state)
            else:
                reset_state.last_reset_key = current_reset_key

        await session.commit()