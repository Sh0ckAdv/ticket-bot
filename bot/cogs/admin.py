import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from bot.db.models import GuildSettings
from bot.db.session import AsyncSessionLocal


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="ticketsetup2",
        description="Configurează sistemul de tickete pentru acest server.",
    )
    @app_commands.describe(
        password_category="Categoria pentru ticketele de recuperare parolă",
        general_category="Categoria pentru ticketele generale",
        unban_category="Categoria pentru cererile unban",
        logs_channel="Canalul unde vor fi trimise log-urile",
        transcripts_channel="Canalul unde vor fi trimise transcript-urile",
        password_support_role="Rolul care poate vedea ticketele de recuperare parolă",
        discord_staff_role="Rolul staff pentru ticketele generale și cererile unban",
        manager_discord_role="Rolul manager pentru ticketele generale și cererile unban",
        max_open_tickets="Numărul maxim de tickete deschise per utilizator",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def ticketsetup(
        self,
        interaction: discord.Interaction,
        password_category: discord.CategoryChannel,
        general_category: discord.CategoryChannel,
        unban_category: discord.CategoryChannel,
        logs_channel: discord.TextChannel,
        transcripts_channel: discord.TextChannel,
        password_support_role: discord.Role,
        discord_staff_role: discord.Role,
        manager_discord_role: discord.Role,
        max_open_tickets: app_commands.Range[int, 1, 10],
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Această comandă poate fi folosită doar pe un server.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(GuildSettings).where(GuildSettings.guild_id == interaction.guild.id)
            )
            settings = result.scalar_one_or_none()

            if settings is None:
                settings = GuildSettings(
                    guild_id=interaction.guild.id,
                    password_category_id=password_category.id,
                    general_category_id=general_category.id,
                    unban_category_id=unban_category.id,
                    logs_channel_id=logs_channel.id,
                    transcripts_channel_id=transcripts_channel.id,
                    password_support_role_id=password_support_role.id,
                    discord_staff_role_id=discord_staff_role.id,
                    manager_discord_role_id=manager_discord_role.id,
                    max_open_tickets_per_user=max_open_tickets,
                    is_enabled=True,
                )
                session.add(settings)
            else:
                settings.password_category_id = password_category.id
                settings.general_category_id = general_category.id
                settings.unban_category_id = unban_category.id
                settings.logs_channel_id = logs_channel.id
                settings.transcripts_channel_id = transcripts_channel.id
                settings.password_support_role_id = password_support_role.id
                settings.discord_staff_role_id = discord_staff_role.id
                settings.manager_discord_role_id = manager_discord_role.id
                settings.max_open_tickets_per_user = max_open_tickets
                settings.is_enabled = True

            await session.commit()

        embed = discord.Embed(
            title="Sistemul de tickete a fost configurat",
            description="Configurarea a fost salvată cu succes.",
            color=discord.Color.green(),
        )
        embed.add_field(name="Categorie Recuperare Parolă", value=password_category.mention, inline=False)
        embed.add_field(name="Categorie Ticket", value=general_category.mention, inline=False)
        embed.add_field(name="Categorie Cerere Unban", value=unban_category.mention, inline=False)
        embed.add_field(name="Canal Log-uri", value=logs_channel.mention, inline=False)
        embed.add_field(name="Canal Transcript-uri", value=transcripts_channel.mention, inline=False)
        embed.add_field(name="Rol Recuperare Parolă", value=password_support_role.mention, inline=False)
        embed.add_field(name="Rol Discord Staff", value=discord_staff_role.mention, inline=False)
        embed.add_field(name="Rol Manager Discord", value=manager_discord_role.mention, inline=False)
        embed.add_field(name="Limită Tickete / Utilizator", value=str(max_open_tickets), inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @ticketsetup.error
    async def ticketsetup_error(
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
    await bot.add_cog(Admin(bot))