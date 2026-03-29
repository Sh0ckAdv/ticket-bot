import discord
from discord.ext import commands
from discord import app_commands

import os
from dotenv import load_dotenv

load_dotenv()

GUILD_ID = int(os.getenv("GUILD_ID", "0"))
MY_GUILD = discord.Object(id=GUILD_ID) 

PANEL_CHANNEL_ID = 1487184469348712552
ROLE_ID = 1487184621975371847

class EventDuminicaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Ia rolul",
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="event_duminica_add_role"
    )
    async def add_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(ROLE_ID)

        if role is None:
            await interaction.response.send_message("Rolul nu a fost găsit.", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.response.send_message(
                f"Ai deja rolul {role.mention}.",
                ephemeral=True
            )
            return

        await interaction.user.add_roles(role)
        await interaction.response.send_message(
            f"Ai primit rolul {role.mention} ✅",
            ephemeral=True
        )

    @discord.ui.button(
        label="Renunță la rol",
        style=discord.ButtonStyle.danger,
        emoji="❌",
        custom_id="event_duminica_remove_role"
    )
    async def remove_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(ROLE_ID)

        if role is None:
            await interaction.response.send_message("Rolul nu a fost găsit.", ephemeral=True)
            return

        if role not in interaction.user.roles:
            await interaction.response.send_message(
                f"Nu ai rolul {role.mention}.",
                ephemeral=True
            )
            return

        await interaction.user.remove_roles(role)
        await interaction.response.send_message(
            f"Ți-am scos rolul {role.mention} ❌",
            ephemeral=True
        )


class EventDuminica(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="eventpiratpanel",
        description="Trimite panoul pentru event."
    )
    @app_commands.guilds(MY_GUILD)
    @app_commands.checks.has_permissions(administrator=True)
    async def eventpiratpanel(self, interaction: discord.Interaction):
        channel = self.bot.get_channel(PANEL_CHANNEL_ID)

        if channel is None:
            await interaction.response.send_message(
                "Nu am găsit canalul setat.",
                ephemeral=True
            )
            return

        bot_avatar = self.bot.user.display_avatar.url if self.bot.user else None

        embed = discord.Embed(
            title="🏴‍☠️ Event Special",
            description=(
                "📢 **CAUTAREA DE COMORI** 🗺️\n\n"
                "Daca vreti sa participati la eventul Cautarea de Comori, "
                "va rog sa apasati mai jos ca sa primiti rolul unde puteti vedea "
                "canalul unde se vor posta zilnic aceste indicii. 🔎✨"
            ),
            color=discord.Color.gold()
        )

        if bot_avatar:
            embed.set_thumbnail(url=bot_avatar)
            embed.set_footer(
                text=self.bot.user.name,
                icon_url=bot_avatar
            )

        view = EventDuminicaView()
        await channel.send(embed=embed, view=view)

        await interaction.response.send_message(
            f"Panel trimis în <#{PANEL_CHANNEL_ID}> ✅",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(EventDuminica(bot))
    bot.add_view(EventDuminicaView())