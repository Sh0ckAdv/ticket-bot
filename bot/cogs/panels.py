import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from bot.db.models import GuildSettings, TicketPanel
from bot.db.session import AsyncSessionLocal
from bot.ui.panel_views import TicketPanelView

import os
from dotenv import load_dotenv

load_dotenv()

GUILD_ID = int(os.getenv("GUILD_ID", "0"))
MY_GUILD = discord.Object(id=GUILD_ID) 

class Panels(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="sendpanel",
        description="Trimite panoul principal de tickete într-un canal.",
    )
    @app_commands.describe(
        channel="Canalul în care va fi trimis panoul de tickete",
    )
    @app_commands.guilds(MY_GUILD)
    @app_commands.checks.has_permissions(administrator=True)
    async def sendpanel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
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
                await interaction.followup.send(
                    "Sistemul de tickete nu este configurat încă. Folosește mai întâi `/ticketsetup`.",
                    ephemeral=True,
                )
                return

            embed = discord.Embed(
                title="mc.ratonii.ro | tickets",
                description=(
                    "Pentru probleme legate de server-ul de Minecraft, vă rugăm să\n"
                    "intrați pe https://panel.ratonii.ro\n\n"
                    "Alege categoria potrivită problemei tale:"
                ),
                color=discord.Color.from_rgb(221, 255, 153),
            )

            if self.bot.user and self.bot.user.display_avatar:
                embed.set_thumbnail(url=self.bot.user.display_avatar.url)

            embed.add_field(
                name="🔐 Recuperare Parolă",
                value="`Deschide un ticket pentru probleme legate de cont sau parolă.`",
                inline=False,
            )
            embed.add_field(
                name="🎫 Ticket",
                value="`Deschide un ticket pentru probleme generale legate de Discord.`",
                inline=False,
            )
            embed.add_field(
                name="🔨 Cerere Unban",
                value="`Deschide un ticket pentru a face apel la o sancțiune.`",
                inline=False,
            )

            embed.set_footer(
                text="a mc.ratonii.ro experience - nu deschide tickete inutile",
                icon_url=self.bot.user.display_avatar.url if self.bot.user else None,
            )

            message = await channel.send(
                embed=embed,
                view=TicketPanelView(),
            )

            panel_result = await session.execute(
                select(TicketPanel).where(TicketPanel.guild_id == interaction.guild.id)
            )
            existing_panel = panel_result.scalar_one_or_none()

            if existing_panel is None:
                panel = TicketPanel(
                    guild_id=interaction.guild.id,
                    channel_id=channel.id,
                    message_id=message.id,
                    title="mc.ratonii.ro | tickets",
                    description="Panoul principal de tickete",
                )
                session.add(panel)
            else:
                existing_panel.channel_id = channel.id
                existing_panel.message_id = message.id
                existing_panel.title = "mc.ratonii.ro | tickets"
                existing_panel.description = "Panoul principal de tickete"

            await session.commit()

        await interaction.followup.send(
            f"Panoul de tickete a fost trimis cu succes în {channel.mention}.",
            ephemeral=True,
        )

    @sendpanel.error
    async def sendpanel_error(
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
    await bot.add_cog(Panels(bot))