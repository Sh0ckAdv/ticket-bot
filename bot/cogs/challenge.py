import asyncio
import random
import time
from dataclasses import dataclass
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands


ALLOWED_CHANNEL_ID = 1463329532730933483

ACCEPT_TIMEOUT = 30
TYPE_TIMEOUT = 45

CHALLENGE_WORDS = [
    "paralelipiped",
    "electrocasnice",
    "interconectare",
    "extraordinar",
    "incompatibilitate",
    "responsabilitate",
    "reconfigurare",
    "implementare",
    "configuratie",
    "reprezentativ",
    "telecomunicatii",
    "dezamagitor",
    "neintrerupt",
    "bibliotecara",
    "microprocesoare",
    "individualizare",
    "reorganizare",
    "caracteristica",
    "infrastructura",
    "autentificare",
    "performanta",
    "administratie",
    "spectaculos",
    "incredibilitate",
    "dezvoltator",
    "conversational",
    "profesionalism",
    "imposibilitate",
    "stabilitate",
    "comportament",
    "matematica",
    "constitutional",
    "neconventional",
    "extraordinara",
    "compatibilitate",
    "contabilitate",
    "participare",
    "perseverenta",
    "independenta",
    "efervescenta",
    "aproximativ",
    "monitorizare",
    "performantei",
    "concentrare",
    "administrativ",
    "fundamental",
    "instantaneu",
    "circumstanta",
    "determinare",
    "recompensare",
    "deconectare",
    "suplimentare",
    "intermediere",
    "surprinzator",
    "extraoptimizare",
    "dezorganizare",
    "responsabil",
    "reactualizare",
    "functionalitate",
    "dezinstalare",
    "reabilitare",
    "profunzime",
    "clarificare",
    "recunoastere",
    "confruntare",
    "prescurtare",
    "expozitional",
    "inregistrare",
    "consolidare",
    "reintregire",
    "ratiune",
    "atragatoare",
    "spectator",
    "instructiune",
    "interactiune",
    "specializare",
    "organizatoric",
    "experimentare",
    "inteligenta",
    "conectivitate",
    "arhitectura",
    "simultanitate",
    "posibilitate",
    "vizualizare",
    "personalizare",
    "reconstructie",
    "transmitere",
    "confirmare",
    "dezvoltare",
    "flexibilitate",
    "coordonare",
    "delimitare",
    "echilibrare",
    "fundamentare",
    "interpretare",
    "rationament",
    "sincronizare",
    "transformare",
    "verificare",
]


@dataclass
class ActiveChallenge:
    guild_id: int
    channel_id: int
    challenger_id: int
    opponent_id: int
    word: str
    created_at: float
    started: bool = False
    finished: bool = False
    message_id: Optional[int] = None
    winner_id: Optional[int] = None
    started_at: Optional[float] = None


class ChallengeInviteView(discord.ui.View):
    def __init__(self, cog: "ChallengeCog", challenge: ActiveChallenge):
        super().__init__(timeout=ACCEPT_TIMEOUT)
        self.cog = cog
        self.challenge = challenge

    async def disable_all(self):
        for item in self.children:
            item.disabled = True

    async def on_timeout(self):
        if self.challenge.finished or self.challenge.started:
            return

        self.challenge.finished = True
        await self.disable_all()

        channel = self.cog.bot.get_channel(self.challenge.channel_id)
        if channel and isinstance(channel, discord.TextChannel):
            try:
                msg = await channel.fetch_message(self.challenge.message_id)
                embed = discord.Embed(
                    title="⌛ Challenge expirat",
                    description=(
                        f"<@{self.challenge.opponent_id}> nu a răspuns la timp provocării lui "
                        f"<@{self.challenge.challenger_id}>."
                    ),
                    color=discord.Color.orange(),
                )
                await msg.edit(embed=embed, view=self)
            except Exception:
                pass

        self.cog.remove_challenge(self.challenge.channel_id)

    @discord.ui.button(label="Acceptă", style=discord.ButtonStyle.success)
    async def accept_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.challenge.opponent_id:
            await interaction.response.send_message(
                "Doar jucătorul provocat poate accepta acest challenge.",
                ephemeral=True,
            )
            return

        if self.challenge.finished or self.challenge.started:
            await interaction.response.send_message(
                "Acest challenge nu mai este disponibil.",
                ephemeral=True,
            )
            return

        self.challenge.started = True
        self.challenge.started_at = time.time()

        await self.disable_all()

        embed = discord.Embed(
            title="⚔️ Challenge început",
            description=(
                f"{interaction.user.mention} a acceptat provocarea lui "
                f"<@{self.challenge.challenger_id}>.\n\n"
                f"✍️ Primul care scrie corect în chat cuvântul de mai jos câștigă:\n\n"
                f"```{self.challenge.word}```\n"
                f"⏳ Aveți **{TYPE_TIMEOUT} secunde**."
            ),
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="Jucători",
            value=(
                f"**Provocator:** <@{self.challenge.challenger_id}>\n"
                f"**Provocat:** <@{self.challenge.opponent_id}>"
            ),
            inline=False,
        )
        embed.set_footer(text="Scrie cuvântul exact cum apare.")

        await interaction.response.edit_message(embed=embed, view=self)

        self.cog.bot.loop.create_task(
            self.cog.challenge_type_timeout(self.challenge.channel_id)
        )

    @discord.ui.button(label="Refuză", style=discord.ButtonStyle.danger)
    async def decline_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.challenge.opponent_id:
            await interaction.response.send_message(
                "Doar jucătorul provocat poate refuza acest challenge.",
                ephemeral=True,
            )
            return

        if self.challenge.finished or self.challenge.started:
            await interaction.response.send_message(
                "Acest challenge nu mai este disponibil.",
                ephemeral=True,
            )
            return

        self.challenge.finished = True
        await self.disable_all()

        embed = discord.Embed(
            title="❌ Challenge refuzat",
            description=(
                f"{interaction.user.mention} a refuzat provocarea lui "
                f"<@{self.challenge.challenger_id}>."
            ),
            color=discord.Color.red(),
        )

        await interaction.response.edit_message(embed=embed, view=self)
        self.cog.remove_challenge(self.challenge.channel_id)


class ChallengeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_challenges: dict[int, ActiveChallenge] = {}

    def remove_challenge(self, channel_id: int):
        self.active_challenges.pop(channel_id, None)

    def get_challenge(self, channel_id: int) -> Optional[ActiveChallenge]:
        return self.active_challenges.get(channel_id)

    async def challenge_type_timeout(self, channel_id: int):
        await asyncio.sleep(TYPE_TIMEOUT)

        challenge = self.get_challenge(channel_id)
        if not challenge:
            return
        if challenge.finished or not challenge.started:
            return

        challenge.finished = True

        channel = self.bot.get_channel(channel_id)
        if channel and isinstance(channel, discord.TextChannel):
            embed = discord.Embed(
                title="⌛ Nimeni nu a câștigat",
                description=(
                    f"Niciun jucător nu a scris corect cuvântul la timp.\n\n"
                    f"Cuvântul era:\n```{challenge.word}```"
                ),
                color=discord.Color.orange(),
            )
            await channel.send(embed=embed)

        self.remove_challenge(channel_id)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return
        if message.channel.id != ALLOWED_CHANNEL_ID:
            return

        challenge = self.get_challenge(message.channel.id)
        if not challenge:
            return
        if challenge.finished or not challenge.started:
            return

        if message.author.id not in {challenge.challenger_id, challenge.opponent_id}:
            return

        typed = message.content.strip()
        if typed != challenge.word:
            return

        challenge.finished = True
        challenge.winner_id = message.author.id

        elapsed = None
        if challenge.started_at:
            elapsed = round(time.time() - challenge.started_at, 2)

        loser_id = (
            challenge.opponent_id
            if message.author.id == challenge.challenger_id
            else challenge.challenger_id
        )

        embed = discord.Embed(
            title="🏆 Avem un câștigător!",
            description=(
                f"{message.author.mention} a scris primul corect cuvântul și a câștigat challenge-ul."
            ),
            color=discord.Color.green(),
        )
        embed.add_field(name="Cuvânt", value=f"```{challenge.word}```", inline=False)
        embed.add_field(
            name="Rezultat",
            value=(
                f"**Câștigător:** <@{message.author.id}>\n"
                f"**Pierzător:** <@{loser_id}>"
            ),
            inline=False,
        )
        if elapsed is not None:
            embed.set_footer(text=f"Timp de reacție: {elapsed} secunde")

        await message.channel.send(embed=embed)
        self.remove_challenge(message.channel.id)

    @app_commands.command(
        name="challenge",
        description="Provoacă un jucător la un challenge de scris rapid."
    )
    async def challenge(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
    ):
        if not interaction.guild or not interaction.channel:
            await interaction.response.send_message(
                "Comanda poate fi folosită doar pe server.",
                ephemeral=True,
            )
            return

        if interaction.channel.id != ALLOWED_CHANNEL_ID:
            await interaction.response.send_message(
                f"Folosește comanda doar pe canalul <#{ALLOWED_CHANNEL_ID}>.",
                ephemeral=True,
            )
            return

        if user.bot:
            await interaction.response.send_message(
                "Nu poți provoca un bot.",
                ephemeral=True,
            )
            return

        if user.id == interaction.user.id:
            await interaction.response.send_message(
                "Nu poți să îți dai challenge singur.",
                ephemeral=True,
            )
            return

        existing = self.get_challenge(interaction.channel.id)
        if existing and not existing.finished:
            await interaction.response.send_message(
                "Există deja un challenge activ sau în așteptare pe acest canal.",
                ephemeral=True,
            )
            return

        word = random.choice(CHALLENGE_WORDS)

        challenge = ActiveChallenge(
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            challenger_id=interaction.user.id,
            opponent_id=user.id,
            word=word,
            created_at=time.time(),
        )
        self.active_challenges[interaction.channel.id] = challenge

        view = ChallengeInviteView(self, challenge)

        embed = discord.Embed(
            title="⚔️ Challenge nou",
            description=(
                f"{interaction.user.mention} l-a provocat pe {user.mention} la un duel de scris.\n\n"
                f"{user.mention}, ai **{ACCEPT_TIMEOUT} secunde** să accepți sau să refuzi."
            ),
            color=discord.Color.gold(),
        )
        embed.add_field(
            name="Cum funcționează",
            value=(
                "După acceptare, botul va afișa un cuvânt.\n"
                "Primul dintre voi doi care îl scrie **exact corect** în chat câștigă."
            ),
            inline=False,
        )
        embed.set_footer(text="Challenge de viteză")

        await interaction.response.send_message(
            content=user.mention,
            embed=embed,
            view=view,
        )

        try:
            sent_message = await interaction.original_response()
            challenge.message_id = sent_message.id
        except Exception:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(ChallengeCog(bot))