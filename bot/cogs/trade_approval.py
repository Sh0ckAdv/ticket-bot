import discord
from discord.ext import commands

SOURCE_CHANNEL_ID = 1192228055679246406
REVIEW_CHANNEL_ID = 1425110448721629335

ALLOWED_ROLE_IDS = {
    1093217111876325406,
    1129501329740533883,
}


class TradeApprovalView(discord.ui.View):
    def __init__(
        self,
        source_channel_id: int,
        author_id: int,
        trade_text: str,
        attachments: list[str] | None = None,
    ):
        super().__init__(timeout=None)
        self.source_channel_id = source_channel_id
        self.author_id = author_id
        self.trade_text = trade_text
        self.attachments = attachments or []

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "❌ Doar membrii serverului pot folosi aceste butoane.",
                ephemeral=True
            )
            return False

        if not any(role.id in ALLOWED_ROLE_IDS for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ Nu ai acces la aceste butoane.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Accepta", style=discord.ButtonStyle.success, emoji="✅")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        source_channel = interaction.guild.get_channel(self.source_channel_id) if interaction.guild else None

        if not isinstance(source_channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Canalul sursă nu a fost găsit.",
                ephemeral=True
            )
            return

        result_embed = discord.Embed(
            title="📦 Cerere de trade",
            description=(
                f"**<@{self.author_id}>**\n\n"
                f"{self.trade_text}"
            ),
            color=discord.Color.blurple(),
        )

        if self.attachments:
            result_embed.add_field(
                name="Atașamente",
                value="\n".join(self.attachments[:10]),
                inline=False
            )

        await source_channel.send(embed=result_embed)

        for item in self.children:
            item.disabled = True

        approved_embed = discord.Embed(
            title="✅ Cerere aprobată",
            description=(
                f"**Utilizator:** <@{self.author_id}>\n"
                f"**Aprobat de:** {interaction.user.mention}\n"
                f"**Trade:**\n{self.trade_text}"
            ),
            color=discord.Color.green(),
        )

        if self.attachments:
            approved_embed.add_field(
                name="Atașamente",
                value="\n".join(self.attachments[:10]),
                inline=False
            )

        await interaction.response.edit_message(embed=approved_embed, view=self)

    @discord.ui.button(label="Refuza", style=discord.ButtonStyle.danger, emoji="❌")
    async def refuse_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True

        refused_embed = discord.Embed(
            title="❌ Cerere refuzată",
            description=(
                f"**Utilizator:** <@{self.author_id}>\n"
                f"**Refuzat de:** {interaction.user.mention}\n"
                f"**Trade:**\n{self.trade_text}"
            ),
            color=discord.Color.red(),
        )

        if self.attachments:
            refused_embed.add_field(
                name="Atașamente",
                value="\n".join(self.attachments[:10]),
                inline=False
            )

        await interaction.response.edit_message(embed=refused_embed, view=self)


class TradeApproval(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if not message.guild:
            return

        if message.channel.id != SOURCE_CHANNEL_ID:
            return

        review_channel = message.guild.get_channel(REVIEW_CHANNEL_ID)
        if not isinstance(review_channel, discord.TextChannel):
            return

        trade_text = message.content.strip() if message.content.strip() else "*Fără text*"
        attachment_urls = [a.url for a in message.attachments]

        embed = discord.Embed(
            title="📩 Cerere nouă pentru aprobare",
            description=(
                f"**Utilizator:** {message.author.mention}\n"
                f"**Canal sursă:** {message.channel.mention}\n\n"
                f"**Trade dorit:**\n{trade_text}"
            ),
            color=discord.Color.blurple(),
        )

        if attachment_urls:
            embed.add_field(
                name="Atașamente",
                value="\n".join(attachment_urls[:10]),
                inline=False
            )

        embed.set_footer(text=f"User ID: {message.author.id}")

        view = TradeApprovalView(
            source_channel_id=message.channel.id,
            author_id=message.author.id,
            trade_text=trade_text,
            attachments=attachment_urls,
        )

        await review_channel.send(embed=embed, view=view)

        try:
            await message.delete()
        except discord.Forbidden:
            pass
        except discord.NotFound:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(TradeApproval(bot))