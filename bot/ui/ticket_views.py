from __future__ import annotations
import asyncio

import discord
from datetime import datetime, timezone
from sqlalchemy import select

from bot.db.models import GuildSettings, StaffPoint, Ticket
from bot.db.session import AsyncSessionLocal
from bot.services.transcript_service import build_transcript_file


class CloseConfirmView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=120)

    @discord.ui.button(
        label="Rezolvat",
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="ticket_close_resolved",
    )
    async def resolved(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await self._close_ticket(interaction, resolved=True)

    @discord.ui.button(
        label="Nu a fost rezolvat",
        style=discord.ButtonStyle.secondary,
        emoji="❌",
        custom_id="ticket_close_unresolved",
    )
    async def unresolved(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await self._close_ticket(interaction, resolved=False)

    async def _close_ticket(
        self,
        interaction: discord.Interaction,
        resolved: bool,
    ) -> None:
        if interaction.guild is None or interaction.channel is None:
            return

        await interaction.response.defer()

        channel = interaction.channel

        async with AsyncSessionLocal() as session:
            settings_result = await session.execute(
                select(GuildSettings).where(GuildSettings.guild_id == interaction.guild.id)
            )
            settings = settings_result.scalar_one_or_none()

            ticket_result = await session.execute(
                select(Ticket).where(Ticket.channel_id == channel.id)
            )
            ticket = ticket_result.scalar_one_or_none()

            if settings is None or ticket is None:
                await interaction.followup.send(
                    "Nu am găsit setările sau ticketul în baza de date.",
                    ephemeral=True,
                )
                return

            if ticket.status == "closed":
                await interaction.followup.send(
                    "Ticketul este deja închis.",
                    ephemeral=True,
                )
                return

            transcript_file = await build_transcript_file(channel)

            ticket.status = "closed"
            ticket.closed_by = interaction.user.id
            ticket.closed_at = datetime.now(timezone.utc)

            if resolved:
                staff_points_result = await session.execute(
                    select(StaffPoint).where(
                        StaffPoint.guild_id == interaction.guild.id,
                        StaffPoint.user_id == interaction.user.id,
                    )
                )
                staff_points = staff_points_result.scalar_one_or_none()

                if staff_points is None:
                    staff_points = StaffPoint(
                        guild_id=interaction.guild.id,
                        user_id=interaction.user.id,
                        points=1,
                    )
                    session.add(staff_points)
                else:
                    staff_points.points += 1

            await session.commit()
        creator = interaction.guild.get_member(ticket.creator_id)
        closer = interaction.user

        status_text = "Rezolvat" if resolved else "Nu a fost rezolvat"
        status_color = discord.Color.green() if resolved else discord.Color.red()

        transcripts_channel = interaction.guild.get_channel(settings.transcripts_channel_id)
        logs_channel = interaction.guild.get_channel(settings.logs_channel_id)

        transcript_embed = discord.Embed(
            title="Transcript ticket",
            description=(
                f"Ticketul **{channel.name}** a fost închis.\n"
                f"**Status:** {status_text}"
            ),
            color=status_color,
            timestamp=datetime.now(timezone.utc),
        )
        transcript_embed.add_field(
            name="Creator",
            value=creator.mention if creator else f"`{ticket.creator_id}`",
            inline=True,
        )
        transcript_embed.add_field(
            name="Închis de",
            value=closer.mention,
            inline=True,
        )
        transcript_embed.add_field(
            name="Tip ticket",
            value=ticket.ticket_type,
            inline=True,
        )
        transcript_embed.set_footer(text="Ratonii Tickets")

        if transcripts_channel and isinstance(transcripts_channel, discord.TextChannel):
            await transcripts_channel.send(embed=transcript_embed, file=transcript_file)

        log_embed = discord.Embed(
            title="Ticket închis",
            description=f"Canalul **{channel.name}** va fi șters automat.",
            color=status_color,
            timestamp=datetime.now(timezone.utc),
        )
        log_embed.add_field(
            name="Creator",
            value=creator.mention if creator else f"`{ticket.creator_id}`",
            inline=True,
        )
        log_embed.add_field(
            name="Închis de",
            value=closer.mention,
            inline=True,
        )
        log_embed.add_field(
            name="Status final",
            value=status_text,
            inline=True,
        )
        log_embed.set_footer(text="Ratonii Tickets")

        if logs_channel and isinstance(logs_channel, discord.TextChannel):
            await logs_channel.send(embed=log_embed)

        close_embed = discord.Embed(
            title="Ticket închis",
            description=(
                f"Ticketul a fost închis de {closer.mention}.\n"
                f"**Status:** {status_text}\n\n"
                "Canalul va fi șters în 5 secunde."
            ),
            color=status_color,
            timestamp=datetime.now(timezone.utc),
        )
        close_embed.set_footer(text="Ratonii Tickets")

        await channel.send(embed=close_embed)

        for item in self.children:
            item.disabled = True

        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass

        self.stop()

        await asyncio.sleep(5)
        await channel.delete(reason=f"Ticket închis de {closer}")


class TicketView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    async def _is_staff_allowed(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            return False

        async with AsyncSessionLocal() as session:
            settings_result = await session.execute(
                select(GuildSettings).where(GuildSettings.guild_id == interaction.guild.id)
            )
            settings = settings_result.scalar_one_or_none()

            ticket_result = await session.execute(
                select(Ticket).where(Ticket.channel_id == interaction.channel.id)
            )
            ticket = ticket_result.scalar_one_or_none()

        if settings is None or ticket is None:
            return False

        allowed_role_ids: set[int] = set()

        if ticket.ticket_type == "password":
            if settings.password_support_role_id:
                allowed_role_ids.add(settings.password_support_role_id)
        else:
            if settings.discord_staff_role_id:
                allowed_role_ids.add(settings.discord_staff_role_id)
            if settings.manager_discord_role_id:
                allowed_role_ids.add(settings.manager_discord_role_id)

        member_role_ids = {role.id for role in interaction.user.roles}
        return bool(allowed_role_ids & member_role_ids)

    @discord.ui.button(
        label="Claim",
        style=discord.ButtonStyle.success,
        emoji="👤",
        custom_id="ticket_claim",
    )
    async def claim(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if interaction.guild is None or interaction.channel is None:
            return

        allowed = await self._is_staff_allowed(interaction)
        if not allowed:
            await interaction.response.send_message(
                "Nu ai permisiunea să preiei acest ticket.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Ticket).where(Ticket.channel_id == interaction.channel.id)
            )
            ticket = result.scalar_one_or_none()

            if ticket is None:
                await interaction.followup.send(
                    "Nu am găsit ticketul în baza de date.",
                    ephemeral=True,
                )
                return

            if ticket.claimed_by:
                claimed_member = interaction.guild.get_member(ticket.claimed_by)
                claimed_text = claimed_member.mention if claimed_member else "alt membru staff"
                await interaction.followup.send(
                    f"Ticketul este deja preluat de {claimed_text}.",
                    ephemeral=True,
                )
                return

            ticket.claimed_by = interaction.user.id
            await session.commit()

        embed = discord.Embed(
            title="Ticket preluat",
            description=(
                f"{interaction.user.mention} a preluat acest ticket.\n"
                "Un membru din staff se ocupă acum de această cerere."
            ),
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text="Ratonii Tickets")

        await interaction.channel.send(embed=embed)

    @discord.ui.button(
        label="Închide",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="ticket_close",
    )
    async def close(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if interaction.guild is None or interaction.channel is None:
            return

        allowed = await self._is_staff_allowed(interaction)
        if not allowed:
            await interaction.response.send_message(
                "Nu ai permisiunea să închizi acest ticket.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="Confirmare închidere ticket",
            description="Alege statusul cu care vrei să închizi acest ticket.",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(
            name="Opțiuni",
            value="✅ **Rezolvat**\n❌ **Nu a fost rezolvat**",
            inline=False,
        )
        embed.set_footer(text="Ratonii Tickets")

        await interaction.response.send_message(
            embed=embed,
            view=CloseConfirmView(),
        )