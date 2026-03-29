import random
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import discord
from discord.ext import commands, tasks
from discord import app_commands

# =========================
# CONFIG
# =========================

TARGET_CHANNEL_ID = 1133364222164729978  # <- pune aici ID-ul canalului

try:
    TIMEZONE = ZoneInfo("Europe/Bucharest")
except ZoneInfoNotFoundError:
    TIMEZONE = timezone(timedelta(hours=2))

VOTE_DURATION = 60  # 1 minut
AUTO_POST_EVERY_MINUTES = 15

AM_NAM_QUESTIONS = [
    "Am / N-am luat o notă mică la școală",
    "Am / N-am copiat vreodată la un test",
    "Am / N-am adormit la ore",
    "Am / N-am întârziat la școală",
    "Am / N-am uitat tema acasă",
    "Am / N-am mâncat în timpul orei",
    "Am / N-am chiulit vreodată",
    "Am / N-am fost prins vorbind la oră",
]

# Ore active: 07:00 -> 23:59
START_HOUR = 7
END_HOUR_EXCLUSIVE = 24  # pana la 23:59 inclus


# =========================
# VIEW
# =========================

class AmNamView(discord.ui.View):
    def __init__(self, question: str):
        super().__init__(timeout=VOTE_DURATION)
        self.question = question
        self.votes: dict[int, str] = {}  # user_id -> "am" / "nam"
        self.message: discord.Message | None = None
        self.finished = False
        self.refresh_labels()

    def refresh_labels(self):
        am_count = sum(1 for vote in self.votes.values() if vote == "am")
        nam_count = sum(1 for vote in self.votes.values() if vote == "nam")

        for item in self.children:
            if isinstance(item, discord.ui.Button):
                if item.custom_id == "am_button":
                    item.label = f"Am ({am_count})"
                elif item.custom_id == "nam_button":
                    item.label = f"N-am ({nam_count})"

    def get_vote_lists(self):
        am_users = [user_id for user_id, vote in self.votes.items() if vote == "am"]
        nam_users = [user_id for user_id, vote in self.votes.items() if vote == "nam"]
        return am_users, nam_users

    def format_user_list(self, user_ids: list[int]) -> str:
        if not user_ids:
            return "Nimeni"
        return "\n".join(f"• <@{user_id}>" for user_id in user_ids)

    def build_active_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🎮 Am / N-am",
            description=f"**{self.question}**",
            color=discord.Color.blurple()
        )
        embed.add_field(
            name="⏳ Timp de vot",
            value="1 minut",
            inline=True
        )
        embed.add_field(
            name="📌 Cum votezi",
            value="Apasă pe unul dintre butoanele de mai jos.",
            inline=True
        )
        embed.set_footer(text="Poți să îți schimbi votul până expiră timpul.")
        return embed

    def build_result_embed(self) -> discord.Embed:
        am_users, nam_users = self.get_vote_lists()

        embed = discord.Embed(
            title="📊 Rezultate Am / N-am",
            description=f"**{self.question}**",
            color=discord.Color.green()
        )

        embed.add_field(name="✅ Am", value=str(len(am_users)), inline=True)
        embed.add_field(name="❌ N-am", value=str(len(nam_users)), inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)

        embed.add_field(
            name="✅ Au ales AM",
            value=self.format_user_list(am_users),
            inline=False
        )
        embed.add_field(
            name="❌ Au ales N-AM",
            value=self.format_user_list(nam_users),
            inline=False
        )

        embed.set_footer(text="Votul s-a încheiat.")
        return embed

    async def register_vote(self, interaction: discord.Interaction, choice: str):
        if self.finished:
            await interaction.response.send_message(
                "Votul s-a încheiat deja.",
                ephemeral=True
            )
            return

        self.votes[interaction.user.id] = choice
        self.refresh_labels()

        try:
            if self.message:
                await self.message.edit(view=self)
        except Exception:
            pass

        mesaj = "Ai ales **Am**." if choice == "am" else "Ai ales **N-am**."
        await interaction.response.send_message(mesaj, ephemeral=True)

    @discord.ui.button(
        label="Am (0)",
        style=discord.ButtonStyle.success,
        custom_id="am_button"
    )
    async def am_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.register_vote(interaction, "am")

    @discord.ui.button(
        label="N-am (0)",
        style=discord.ButtonStyle.danger,
        custom_id="nam_button"
    )
    async def nam_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.register_vote(interaction, "nam")

    async def finish_vote(self):
        if self.finished:
            return

        self.finished = True

        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        self.stop()

        if self.message:
            result_embed = self.build_result_embed()
            try:
                await self.message.edit(embed=result_embed, view=self)
            except Exception:
                pass

    async def on_timeout(self):
        await self.finish_vote()


# =========================
# COG
# =========================

class AmNamCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.last_auto_post_key: str | None = None
        self.auto_amnam.start()

    def cog_unload(self):
        self.auto_amnam.cancel()

    def is_active_time(self) -> bool:
        now = datetime.now(TIMEZONE)
        return START_HOUR <= now.hour < END_HOUR_EXCLUSIVE

    def should_post_now(self) -> bool:
        now = datetime.now(TIMEZONE)

        # activ doar intre 07:00 si 23:59
        if not (START_HOUR <= now.hour < END_HOUR_EXCLUSIVE):
            return False

        # doar la fix pe sferturi: 07:00, 07:15, 07:30, 07:45 etc
        if now.minute % AUTO_POST_EVERY_MINUTES != 0:
            return False

        # evitam dublele in acelasi minut
        current_key = now.strftime("%Y-%m-%d %H:%M")
        if self.last_auto_post_key == current_key:
            return False

        self.last_auto_post_key = current_key
        return True

    async def send_amnam(self, channel: discord.TextChannel, question: str):
        view = AmNamView(question=question)
        embed = view.build_active_embed()

        message = await channel.send(embed=embed, view=view)
        view.message = message

    async def get_target_channel(self) -> discord.TextChannel | None:
        channel = self.bot.get_channel(TARGET_CHANNEL_ID)

        if channel is None:
            try:
                channel = await self.bot.fetch_channel(TARGET_CHANNEL_ID)
            except Exception:
                return None

        if not isinstance(channel, discord.TextChannel):
            return None

        return channel

    @tasks.loop(seconds=20)
    async def auto_amnam(self):
        if not self.should_post_now():
            return

        channel = await self.get_target_channel()
        if channel is None:
            print(f"[AM/NAM] Canalul {TARGET_CHANNEL_ID} nu a fost gasit.")
            return

        question = random.choice(AM_NAM_QUESTIONS)

        try:
            await self.send_amnam(channel, question)
            print(f"[AM/NAM] Intrebare trimisa automat la {datetime.now(TIMEZONE).strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"[AM/NAM] Eroare la trimiterea automata: {e}")

    @auto_amnam.before_loop
    async def before_auto_amnam(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="amnamtest", description="Trimite un mesaj de test pentru sistemul Am / N-am.")
    @app_commands.describe(text="Scrie o intrebare custom sau lasa gol pentru una random.")
    @app_commands.checks.has_permissions(administrator=True)
    async def amnamtest(self, interaction: discord.Interaction, text: str | None = None):
        question = text if text else random.choice(AM_NAM_QUESTIONS)

        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "Comanda poate fi folosită doar într-un canal text.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "Am trimis mesajul de test.",
            ephemeral=True
        )

        await self.send_amnam(interaction.channel, question)


# =========================
# SETUP
# =========================

async def setup(bot: commands.Bot):
    await bot.add_cog(AmNamCog(bot))