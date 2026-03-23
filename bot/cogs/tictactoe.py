import discord
from discord.ext import commands
from discord import app_commands


WIN_COMBINATIONS = [
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
]


class TicTacToeButton(discord.ui.Button):
    def __init__(self, position: int):
        super().__init__(
            label="\u200b",
            style=discord.ButtonStyle.secondary,
            row=position // 3
        )
        self.position = position

    async def callback(self, interaction: discord.Interaction):
        view: "TicTacToeGameView" = self.view

        if interaction.user.id not in (view.player_x.id, view.player_o.id):
            await interaction.response.send_message(
                "Nu faci parte din acest meci.",
                ephemeral=True
            )
            return

        if interaction.user.id != view.current_player.id:
            await interaction.response.send_message(
                "Nu este randul tau.",
                ephemeral=True
            )
            return

        if view.board[self.position] is not None:
            await interaction.response.send_message(
                "Casuta este deja ocupata.",
                ephemeral=True
            )
            return

        symbol = "X" if interaction.user.id == view.player_x.id else "O"
        view.board[self.position] = symbol

        self.label = symbol
        self.disabled = True
        self.style = (
            discord.ButtonStyle.danger if symbol == "X"
            else discord.ButtonStyle.success
        )

        winner = view.check_winner()
        if winner:
            view.disable_all_buttons()
            embed = discord.Embed(
                title="X si 0",
                description=(
                    f"🏆 {interaction.user.mention} a castigat!\n\n"
                    f"**X:** {view.player_x.mention}\n"
                    f"**O:** {view.player_o.mention}"
                ),
            )
            await interaction.response.edit_message(embed=embed, view=view)
            view.stop()
            return

        if view.is_draw():
            view.disable_all_buttons()
            embed = discord.Embed(
                title="X si 0",
                description=(
                    "🤝 Egal!\n\n"
                    f"**X:** {view.player_x.mention}\n"
                    f"**O:** {view.player_o.mention}"
                ),
            )
            await interaction.response.edit_message(embed=embed, view=view)
            view.stop()
            return

        view.current_player = (
            view.player_o if view.current_player.id == view.player_x.id
            else view.player_x
        )

        embed = view.build_embed()
        await interaction.response.edit_message(embed=embed, view=view)


class TicTacToeGameView(discord.ui.View):
    def __init__(self, player_x: discord.Member, player_o: discord.Member):
        super().__init__(timeout=180)
        self.player_x = player_x
        self.player_o = player_o
        self.current_player = player_x
        self.board: list[str | None] = [None] * 9
        self.message: discord.Message | None = None

        for i in range(9):
            self.add_item(TicTacToeButton(i))

    def build_embed(self) -> discord.Embed:
        symbol = "X" if self.current_player.id == self.player_x.id else "O"

        embed = discord.Embed(
            title="X si 0",
            description=(
                f"**X:** {self.player_x.mention}\n"
                f"**O:** {self.player_o.mention}\n\n"
                f"Este randul lui {self.current_player.mention} ({symbol})"
            ),
        )
        return embed

    def check_winner(self) -> bool:
        for a, b, c in WIN_COMBINATIONS:
            if (
                self.board[a] is not None and
                self.board[a] == self.board[b] == self.board[c]
            ):
                return True
        return False

    def is_draw(self) -> bool:
        return all(cell is not None for cell in self.board)

    def disable_all_buttons(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    async def on_timeout(self):
        self.disable_all_buttons()

        if self.message:
            embed = discord.Embed(
                title="X si 0",
                description=(
                    "⏰ Meciul a expirat din cauza inactivitatii.\n\n"
                    f"**X:** {self.player_x.mention}\n"
                    f"**O:** {self.player_o.mention}"
                ),
            )
            try:
                await self.message.edit(embed=embed, view=self)
            except discord.HTTPException:
                pass


class TicTacToeChallengeView(discord.ui.View):
    def __init__(self, challenger: discord.Member, opponent: discord.Member):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.opponent = opponent
        self.message: discord.Message | None = None

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message(
                "Doar jucatorul provocat poate accepta.",
                ephemeral=True
            )
            return

        game_view = TicTacToeGameView(self.challenger, self.opponent)
        embed = game_view.build_embed()

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=game_view
        )

        game_view.message = await interaction.original_response()
        self.stop()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message(
                "Doar jucatorul provocat poate refuza.",
                ephemeral=True
            )
            return

        for item in self.children:
            item.disabled = True

        embed = discord.Embed(
            title="X si 0",
            description=(
                f"{self.opponent.mention} a refuzat provocarea lui "
                f"{self.challenger.mention}."
            ),
        )
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        if self.message:
            embed = discord.Embed(
                title="X si 0",
                description=(
                    f"{self.opponent.mention} nu a raspuns la provocarea lui "
                    f"{self.challenger.mention}."
                ),
            )
            try:
                await self.message.edit(embed=embed, view=self)
            except discord.HTTPException:
                pass


class TicTacToe(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    ALLOWED_CHANNEL_ID = 1088801768051327056  # pune ID-ul canalului tau

    @app_commands.command(name="xo", description="Provoaca un jucator la X si 0.")
    async def xo(self, interaction: discord.Interaction, user: discord.Member):
        if interaction.channel_id != ALLOWED_CHANNEL_ID:
            await interaction.response.send_message(
                "❌ Aceasta comanda poate fi folosita doar intr-un canal specific.",
                ephemeral=True
            )
            return

        if user.id == interaction.user.id:
            await interaction.response.send_message(
                "Nu te poti provoca singur.",
                ephemeral=True
            )
            return

        view = TicTacToeChallengeView(interaction.user, user)
        embed = discord.Embed(
            title="X si 0",
            description=(
                f"{interaction.user.mention} l-a provocat pe {user.mention} la X si 0.\n\n"
                f"{user.mention}, apasa pe unul dintre butoanele de mai jos."
            ),
        )

        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()


async def setup(bot: commands.Bot):
    await bot.add_cog(TicTacToe(bot))