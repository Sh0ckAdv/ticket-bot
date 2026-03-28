import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import discord
from discord import app_commands
from discord.ext import commands

CATEGORY_ID = 1376853209066246235
TESTER_ROLE_ID = 1093217111876325406


QUESTIONS = [
    {
        "question": "Ce sancțiune primești pentru reclamă directă sau indirectă?",
        "answers": {
            "A": "MUTE 1h",
            "B": "TIMEOUT 1 zi",
            "C": "BAN PERMANENT",
            "D": "KICK",
        },
        "correct": "C",
    },
    {
        "question": "Este permisă impersonarea altor persoane pe server?",
        "answers": {
            "A": "Da, dacă este în glumă",
            "B": "Da, cu acord verbal",
            "C": "Doar la evenimente",
            "D": "Nu, ban permanent",
        },
        "correct": "D",
    },
    {
        "question": "Ce sancțiune se aplică pentru „Du-te naibii / Du-te dracu”?",
        "answers": {
            "A": "MUTE 10 min",
            "B": "TIMEOUT 20 min",
            "C": "TIMEOUT 1h",
            "D": "BAN",
        },
        "correct": "B",
    },
    {
        "question": "Unde se discută sancțiunile primite?",
        "answers": {
            "A": "Pe chat public",
            "B": "În privat cu alți membri",
            "C": "Pe voice",
            "D": "Doar prin ticket",
        },
        "correct": "D",
    },
    {
        "question": "Ce se întâmplă dacă faci tickete fără motiv?",
        "answers": {
            "A": "Primești avertisment",
            "B": "Sunt ignorate",
            "C": "Se închid instant și ești sancționat",
            "D": "Nu se întâmplă nimic",
        },
        "correct": "C",
    },
    {
        "question": "Ce sancțiune primești pentru spam sau mesaje repetitive?",
        "answers": {
            "A": "TIMEOUT 30 min",
            "B": "MUTE 20 min",
            "C": "MUTE 1h",
            "D": "BAN",
        },
        "correct": "A",
    },
    {
        "question": "Ai voie să dai ping staff-ului fără motiv?",
        "answers": {
            "A": "Da, oricând",
            "B": "Doar o dată",
            "C": "Doar pe voice",
            "D": "Nu",
        },
        "correct": "D",
    },
    {
        "question": "Ce limbă este permisă pe server?",
        "answers": {
            "A": "Orice limbă",
            "B": "Doar română",
            "C": "Doar engleză",
            "D": "Română și engleză",
        },
        "correct": "D",
    },
    {
        "question": "Ce sancțiune se aplică pentru doxxing sau divulgare de date personale?",
        "answers": {
            "A": "MUTE 1h",
            "B": "TIMEOUT 1 zi",
            "C": "WARN",
            "D": "BAN PERMANENT",
        },
        "correct": "D",
    },
    {
        "question": "Un membru folosește caractere obscene prescurtate (ex: injurii mascate).\n\nCe sancțiune se aplică?",
        "answers": {
            "A": "WARN",
            "B": "TIMEOUT 30 min",
            "C": "MUTE 20 min",
            "D": "BAN",
        },
        "correct": "C",
    },
]


@dataclass
class ApplySession:
    candidate_id: int
    tester_id: int
    current_index: int = 0
    correct_count: int = 0
    wrong_count: int = 0
    answers: List[Dict[str, str]] = field(default_factory=list)
    message_id: Optional[int] = None
    finished: bool = False


def sanitize_channel_name(name: str) -> str:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:80] or "user"


class ApplyAnswerButton(discord.ui.Button):
    def __init__(self, letter: str):
        style_map = {
            "A": discord.ButtonStyle.secondary,
            "B": discord.ButtonStyle.primary,
            "C": discord.ButtonStyle.success,
            "D": discord.ButtonStyle.danger,
        }
        super().__init__(
            label=letter,
            style=style_map.get(letter, discord.ButtonStyle.secondary),
            custom_id=f"staff_apply_{letter}",
        )
        self.letter = letter

    async def callback(self, interaction: discord.Interaction) -> None:
        view: "ApplyQuestionView" = self.view  # type: ignore
        view.stop()
        await view.cog.handle_answer(interaction, self.letter)


class FinishTestButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Termină testul",
            style=discord.ButtonStyle.danger,
            custom_id="staff_apply_finish_test",
            emoji="🔒",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        view: "ApplyFinishedView" = self.view  # type: ignore
        await view.finish_test(interaction)


class ApplyQuestionView(discord.ui.View):
    def __init__(self, cog: "StaffApply", channel_id: int, timeout: float = 1800):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.channel_id = channel_id
        self.message: Optional[discord.Message] = None

        self.add_item(ApplyAnswerButton("A"))
        self.add_item(ApplyAnswerButton("B"))
        self.add_item(ApplyAnswerButton("C"))
        self.add_item(ApplyAnswerButton("D"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        session = self.cog.sessions.get(self.channel_id)
        if not session:
            await interaction.response.send_message(
                "❌ Sesiunea acestui test nu mai există.",
                ephemeral=True,
            )
            return False

        if interaction.user.id != session.candidate_id:
            await interaction.response.send_message(
                "❌ Doar utilizatorul testat poate răspunde la acest apply.",
                ephemeral=True,
            )
            return False

        return True

    async def on_timeout(self) -> None:
        session = self.cog.sessions.get(self.channel_id)
        if not session or session.finished:
            return

        for item in self.children:
            item.disabled = True

        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass

        channel = self.cog.bot.get_channel(self.channel_id)
        if isinstance(channel, discord.TextChannel):
            try:
                await channel.send("⏰ Timpul pentru acest apply a expirat.")
            except Exception:
                pass


class ApplyFinishedView(discord.ui.View):
    def __init__(self, cog: "StaffApply", channel_id: int, timeout: float = None):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.channel_id = channel_id
        self.add_item(FinishTestButton())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        member = interaction.user
        if not isinstance(member, discord.Member):
            await interaction.response.send_message(
                "❌ Doar membrii serverului pot folosi acest buton.",
                ephemeral=True,
            )
            return False

        if not any(role.id == TESTER_ROLE_ID for role in member.roles):
            await interaction.response.send_message(
                "❌ Nu ai acces la acest buton.",
                ephemeral=True,
            )
            return False

        return True

    async def finish_test(self, interaction: discord.Interaction) -> None:
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Canal invalid.",
                ephemeral=True,
            )
            return

        session = self.cog.sessions.pop(channel.id, None)

        await interaction.response.send_message(
            "🗑️ Canalul va fi șters...",
            ephemeral=True,
        )

        try:
            await channel.delete(reason=f"Test staff închis de {interaction.user}")
        except Exception:
            pass


class StaffApply(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sessions: Dict[int, ApplySession] = {}

    def build_question_embed(self, member: discord.Member, session: ApplySession) -> discord.Embed:
        data = QUESTIONS[session.current_index]

        description = "\n".join(
            f"**{letter})** {text}"
            for letter, text in data["answers"].items()
        )

        embed = discord.Embed(
            title=f"📝 Staff Apply • Întrebarea {session.current_index + 1}/{len(QUESTIONS)}",
            description=(
                f"**Utilizator:** {member.mention}\n\n"
                f"**{data['question']}**\n\n"
                f"{description}"
            ),
            color=discord.Color.blurple(),
        )
        embed.set_footer(text="Apasă pe butonul corespunzător răspunsului tău.")
        return embed

    def build_result_embed(self, member: discord.Member, session: ApplySession) -> discord.Embed:
        total = len(QUESTIONS)
        percentage = round((session.correct_count / total) * 100, 2)

        if session.wrong_count == 0:
            color = discord.Color.green()
        elif session.wrong_count <= 3:
            color = discord.Color.orange()
        else:
            color = discord.Color.red()

        embed = discord.Embed(
            title="✅ Apply terminat",
            description=(
                f"**Utilizator:** {member.mention}\n"
                f"**Corecte:** {session.correct_count}\n"
                f"**Greșite:** {session.wrong_count}\n"
                f"**Scor:** {percentage}%"
            ),
            color=color,
        )

        details = []
        for index, answer_data in enumerate(session.answers, start=1):
            question_data = QUESTIONS[index - 1]

            selected_letter = answer_data["selected"]
            selected_text = question_data["answers"][selected_letter]

            correct_letter = answer_data["correct"]
            correct_text = question_data["answers"][correct_letter]

            icon = "✅" if answer_data["is_correct"] == "yes" else "❌"

            details.append(
                f"{icon} **Întrebarea {index}:** {question_data['question']}\n"
                f"**Ai ales:** `{selected_letter}` - {selected_text}\n"
                f"**Corect era:** `{correct_letter}` - {correct_text}"
            )

        chunks = []
        current_chunk = ""

        for line in details:
            extra = f"{line}\n\n"
            if len(current_chunk) + len(extra) > 1024:
                chunks.append(current_chunk.strip())
                current_chunk = extra
            else:
                current_chunk += extra

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        for i, chunk in enumerate(chunks, start=1):
            embed.add_field(
                name=f"Rezultate detaliate #{i}",
                value=chunk,
                inline=False,
            )

        embed.set_footer(text="Staff-ul poate apăsa pe „Termină testul”.")
        return embed

    async def handle_answer(self, interaction: discord.Interaction, selected_letter: str) -> None:
        if not interaction.channel or not isinstance(interaction.channel, discord.TextChannel):
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Canal invalid.", ephemeral=True)
            return

        channel_id = interaction.channel.id
        session = self.sessions.get(channel_id)

        if not session:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Sesiunea acestui test nu mai există.",
                    ephemeral=True,
                )
            return

        candidate = interaction.guild.get_member(session.candidate_id) if interaction.guild else None
        if not candidate:
            self.sessions.pop(channel_id, None)
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="❌ Eroare",
                    description="Utilizatorul testat nu mai este disponibil pe server.",
                    color=discord.Color.red(),
                ),
                view=None,
            )
            return

        question_data = QUESTIONS[session.current_index]
        correct_letter = question_data["correct"]
        is_correct = selected_letter == correct_letter

        if is_correct:
            session.correct_count += 1
        else:
            session.wrong_count += 1

        session.answers.append({
            "selected": selected_letter,
            "correct": correct_letter,
            "is_correct": "yes" if is_correct else "no",
        })

        session.current_index += 1

        if session.current_index >= len(QUESTIONS):
            final_embed = self.build_result_embed(candidate, session)
            final_view = ApplyFinishedView(self, channel_id)
            await interaction.response.edit_message(embed=final_embed, view=final_view)
            return

        next_embed = self.build_question_embed(candidate, session)
        new_view = ApplyQuestionView(self, channel_id)

        await interaction.response.edit_message(embed=next_embed, view=new_view)

        try:
            new_view.message = await interaction.original_response()
            session.message_id = new_view.message.id
        except Exception:
            pass

    @app_commands.command(name="test-apply", description="Creează un canal de apply și pornește testul.")
    @app_commands.describe(user="Utilizatorul care va susține testul")
    async def test_apply(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ Comanda poate fi folosită doar pe server.",
                ephemeral=True,
            )
            return

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "❌ Utilizator invalid.",
                ephemeral=True,
            )
            return

        if not any(role.id == TESTER_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ Nu ai rolul necesar pentru a folosi această comandă.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        category = guild.get_channel(CATEGORY_ID)
        tester_role = guild.get_role(TESTER_ROLE_ID)

        if not isinstance(category, discord.CategoryChannel):
            await interaction.followup.send(
                "❌ Categoria setată nu a fost găsită.",
                ephemeral=True,
            )
            return

        if tester_role is None:
            await interaction.followup.send(
                "❌ Rolul setat pentru staff nu a fost găsit.",
                ephemeral=True,
            )
            return

        base_name = f"apply-{sanitize_channel_name(user.name)}"
        channel_name = base_name
        existing_names = {ch.name for ch in category.channels}

        counter = 2
        while channel_name in existing_names:
            channel_name = f"{base_name}-{counter}"
            counter += 1

        bot_member = guild.me or guild.get_member(self.bot.user.id)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            ),
            tester_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True,
            ),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True,
            ),
        }

        if bot_member:
            overwrites[bot_member] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_messages=True,
                embed_links=True,
                attach_files=True,
            )

        channel = await category.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            reason=f"Staff apply creat de {interaction.user} pentru {user}",
        )

        session = ApplySession(
            candidate_id=user.id,
            tester_id=interaction.user.id,
        )
        self.sessions[channel.id] = session

        embed = self.build_question_embed(user, session)
        view = ApplyQuestionView(self, channel.id)

        start_message = await channel.send(
            content=(
                f"{user.mention} ai început testul de staff.\n"
                f"Tester: {interaction.user.mention}"
            ),
            embed=embed,
            view=view,
        )

        view.message = start_message
        session.message_id = start_message.id

        await interaction.followup.send(
            f"✅ Apply-ul a fost creat: {channel.mention}",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StaffApply(bot))