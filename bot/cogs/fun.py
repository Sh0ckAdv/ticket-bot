import random
import discord
from discord.ext import commands
from discord import app_commands

ALLOWED_CHANNEL_ID = 1463329532730933483


class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="compatibility",
        description="Verifică compatibilitatea dintre 2 persoane."
    )
    @app_commands.describe(
        user1="Prima persoană",
        user2="A doua persoană"
    )
    async def compatibility(
        self,
        interaction: discord.Interaction,
        user1: discord.Member,
        user2: discord.Member
    ):
        # Verificare canal
        if interaction.channel_id != ALLOWED_CHANNEL_ID:
            embed = discord.Embed(
                title="❌ Canal greșit",
                description=f"Poți folosi această comandă doar pe <#{ALLOWED_CHANNEL_ID}>.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Verificare bot
        if user1.bot or user2.bot:
            embed = discord.Embed(
                title="🤖 Nu este permis",
                description="Nu poți verifica compatibilitatea cu un bot.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Aceeași persoană
        if user1.id == user2.id:
            embed = discord.Embed(
                title="💘 Rezultat Compatibilitate",
                description=(
                    f"{user1.mention} + {user2.mention}\n\n"
                    f"**Compatibilitate:** `100%`\n"
                    f"Iubirea de sine e importantă 😌"
                ),
                color=discord.Color.pink()
            )
            embed.set_thumbnail(url=user1.display_avatar.url)
            embed.set_footer(
                text=f"Cerut de {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url
            )
            await interaction.response.send_message(embed=embed)
            return

        # Procent random
        percentage = random.randint(1, 100)

        # Mesaje în funcție de procent
        if percentage <= 20:
            emoji = "💔"
            comment = "Nu prea arată bine..."
            color = discord.Color.red()
        elif percentage <= 40:
            emoji = "😅"
            comment = "Există o mică șansă..."
            color = discord.Color.orange()
        elif percentage <= 60:
            emoji = "😊"
            comment = "Nu e rău, există potențial."
            color = discord.Color.gold()
        elif percentage <= 80:
            emoji = "💕"
            comment = "Se simte conexiunea!"
            color = discord.Color.magenta()
        else:
            emoji = "💖"
            comment = "Match perfect, fără dubii!"
            color = discord.Color.pink()

        # Progress bar
        filled = percentage // 10
        empty = 10 - filled
        bar = f"`{'█' * filled}{'░' * empty}`"

        # Embed final
        embed = discord.Embed(
            title="💘 Rezultat Compatibilitate",
            description=(
                f"{user1.mention} **+** {user2.mention}\n\n"
                f"{emoji} **{percentage}%**\n"
                f"{bar}\n\n"
                f"**{comment}**"
            ),
            color=color
        )

        embed.set_thumbnail(url=user1.display_avatar.url)
        embed.set_footer(
            text=f"Cerut de {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))