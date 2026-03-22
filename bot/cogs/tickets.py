import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import desc, select

from bot.db.models import StaffPoint, TicketBlacklist
from bot.db.session import AsyncSessionLocal


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="ticketleaderboard",
        description="Arată leaderboard-ul staff-ului pentru tickete rezolvate.",
    )
    async def ticketleaderboard(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Această comandă poate fi folosită doar pe un server.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(StaffPoint)
                .where(StaffPoint.guild_id == interaction.guild.id)
                .order_by(desc(StaffPoint.points), StaffPoint.user_id)
                .limit(10)
            )
            leaderboard = result.scalars().all()

        if not leaderboard:
            await interaction.followup.send(
                "Nu există încă puncte în leaderboard.",
                ephemeral=False,
            )
            return

        embed = discord.Embed(
            title="Leaderboard Tickete",
            color=discord.Color.gold(),
        )

        lines = []
        for index, entry in enumerate(leaderboard, start=1):
            member = interaction.guild.get_member(entry.user_id)
            name = member.mention if member else f"`{entry.user_id}`"
            lines.append(f"**#{index}** • {name} — **{entry.points}** puncte")

        embed.description = "\n".join(lines)
        embed.set_footer(text="Ratonii Tickets")

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="ticketpoints",
        description="Arată câte puncte are un membru staff.",
    )
    @app_commands.describe(user="Membrul căruia vrei să îi vezi punctele")
    async def ticketpoints(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Această comandă poate fi folosită doar pe un server.",
                ephemeral=True,
            )
            return

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(StaffPoint).where(
                    StaffPoint.guild_id == interaction.guild.id,
                    StaffPoint.user_id == user.id,
                )
            )
            staff_points = result.scalar_one_or_none()

        points = staff_points.points if staff_points else 0

        embed = discord.Embed(
            title="Puncte Staff",
            description=f"{user.mention} are **{points}** puncte.",
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="Ratonii Tickets")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="ticketblacklistadd",
        description="Adaugă un utilizator în blacklist-ul de tickete.",
    )
    @app_commands.describe(
        user="Utilizatorul pe care vrei să îl blochezi",
        reason="Motivul blacklist-ului",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def ticketblacklistadd(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Această comandă poate fi folosită doar pe un server.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        async with AsyncSessionLocal() as session:
            existing_result = await session.execute(
                select(TicketBlacklist).where(
                    TicketBlacklist.guild_id == interaction.guild.id,
                    TicketBlacklist.user_id == user.id,
                )
            )
            existing_entry = existing_result.scalar_one_or_none()

            if existing_entry is not None:
                await interaction.followup.send(
                    f"{user.mention} este deja în blacklist.",
                    ephemeral=True,
                )
                return

            entry = TicketBlacklist(
                guild_id=interaction.guild.id,
                user_id=user.id,
                reason=reason,
                added_by=interaction.user.id,
            )
            session.add(entry)
            await session.commit()

        embed = discord.Embed(
            title="Utilizator adăugat în blacklist",
            color=discord.Color.red(),
        )
        embed.add_field(name="Utilizator", value=user.mention, inline=False)
        embed.add_field(name="Motiv", value=reason, inline=False)
        embed.set_footer(text="Ratonii Tickets")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="ticketblacklistremove",
        description="Scoate un utilizator din blacklist-ul de tickete.",
    )
    @app_commands.describe(
        user="Utilizatorul pe care vrei să îl scoți din blacklist",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def ticketblacklistremove(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Această comandă poate fi folosită doar pe un server.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        async with AsyncSessionLocal() as session:
            existing_result = await session.execute(
                select(TicketBlacklist).where(
                    TicketBlacklist.guild_id == interaction.guild.id,
                    TicketBlacklist.user_id == user.id,
                )
            )
            existing_entry = existing_result.scalar_one_or_none()

            if existing_entry is None:
                await interaction.followup.send(
                    f"{user.mention} nu este în blacklist.",
                    ephemeral=True,
                )
                return

            await session.delete(existing_entry)
            await session.commit()

        embed = discord.Embed(
            title="Utilizator scos din blacklist",
            description=f"{user.mention} poate deschide din nou tickete.",
            color=discord.Color.green(),
        )
        embed.set_footer(text="Ratonii Tickets")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @ticketblacklistadd.error
    @ticketblacklistremove.error
    async def blacklist_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            mesaj = "Ai nevoie de permisiuni de administrator pentru a folosi această comandă."
        else:
            mesaj = f"A apărut o eroare: `{error}`"

        if interaction.response.is_done():
            await interaction.followup.send(mesaj, ephemeral=True)
        else:
            await interaction.response.send_message(mesaj, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Tickets(bot))