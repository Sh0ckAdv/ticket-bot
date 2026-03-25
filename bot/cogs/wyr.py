import asyncio
import random
from typing import Dict, Optional

import discord
from discord.ext import commands, tasks


TARGET_CHANNEL_ID = 1133364222164729978
POLL_DURATION_SECONDS = 30
POST_INTERVAL_MINUTES = 10


WOULD_YOU_RATHER_QUESTIONS = [
    ("Să poți zbura", "Să fii invizibil"),
    ("Să ai bani infiniți", "Să ai timp infinit"),
    ("Să trăiești fără internet", "Să trăiești fără muzică"),
    ("Să poți citi gânduri", "Să poți opri timpul"),
    ("Să mănânci doar pizza", "Să mănânci doar burgeri"),
    ("Să joci doar Minecraft", "Să joci doar GTA V"),
    ("Să nu mai dormi niciodată", "Să nu mai mănânci niciodată"),
    ("Să ai mereu 10% baterie", "Să ai mereu internet lent"),
    ("Să fii foarte faimos", "Să fii foarte bogat"),
    ("Să ai super viteză", "Să ai super putere"),
    ("Să poți vorbi cu animalele", "Să poți vorbi toate limbile"),
    ("Să renunți la TikTok", "Să renunți la YouTube"),
    ("Să ai casă luxoasă", "Să ai mașină de lux"),
    ("Să fii cel mai bun la jocuri", "Să fii cel mai bun la sport"),
    ("Să ai iarnă tot anul", "Să ai vară tot anul"),
    ("Să fii mereu fericit", "Să fii mereu calm"),
    ("Să nu mai ai stres niciodată", "Să nu mai ai griji niciodată"),
    ("Să ai 1 milion acum", "Să ai 10 milioane peste 10 ani"),
    ("Să trăiești în trecut", "Să trăiești în viitor"),
    ("Să ai telefonul perfect", "Să ai PC-ul perfect"),
    ("Să ai prieteni mulți", "Să ai prieteni puțini dar adevărați"),
    ("Să fii mereu ocupat", "Să nu ai nimic de făcut"),
    ("Să câștigi la loto", "Să ai salariu mare constant"),
    ("Să trăiești la munte", "Să trăiești la mare"),
    ("Să ai mașină rapidă", "Să ai mașină luxoasă"),
    ("Să ai tot timpul liber", "Să ai bani nelimitați"),
    ("Să fii celebru pe YouTube", "Să fii celebru pe TikTok"),
    ("Să fii boss la școală", "Să fii boss la muncă"),
    ("Să ai super inteligență", "Să ai super carismă"),
    ("Să fii invulnerabil", "Să te vindeci instant"),
    ("Să vezi viitorul", "Să schimbi trecutul"),
    ("Să ai 100 de ani", "Să ai 50 dar perfect sănătos"),
    ("Să ai jobul visurilor", "Să nu mai muncești niciodată"),
    ("Să ai tot ce vrei", "Să fii mereu fericit"),
    ("Să fii mereu online", "Să nu mai ai internet"),
    ("Să fii lider", "Să fii independent"),
    ("Să ai puterea focului", "Să ai puterea apei"),
    ("Să ai super auz", "Să ai super vedere"),
    ("Să fii bogat dar singur", "Să fii sărac dar cu prieteni"),
    ("Să ai o viață lungă", "Să ai o viață intensă"),
    ("Să ai control asupra timpului", "Să ai control asupra spațiului"),
    ("Să fii cel mai bun la un joc", "Să fii bun la toate"),
    ("Să ai casă mare", "Să ai locație perfectă"),
    ("Să ai libertate totală", "Să ai siguranță totală"),
    ("Să ai succes rapid", "Să ai succes sigur"),
    ("Să fii mereu în centrul atenției", "Să fii liniștit"),
    ("Să ai idei infinite", "Să ai motivație infinită"),
    ("Să fii respectat", "Să fii iubit"),
    ("Să ai putere", "Să ai influență"),
    ("Să fii mereu primul", "Să fii mereu fericit"),
    ("Să ai o viață simplă", "Să ai o viață luxoasă"),
    ("Să fii geniu", "Să fii popular"),
    ("Să ai energie infinită", "Să ai somn perfect"),
    ("Să fii creativ", "Să fii logic"),
    ("Să ai super reflexe", "Să ai super forță"),
    ("Să ai noroc infinit", "Să ai skill infinit"),
    ("Să fii lider de echipă", "Să lucrezi singur"),
    ("Să ai control emoțional", "Să ai pasiune maximă"),
    ("Să ai memorie perfectă", "Să uiți lucrurile rele"),
    ("Să fii rapid", "Să fii precis"),
    ("Să fii calm", "Să fii energic"),
    ("Să ai tot timpul planuri", "Să fii spontan"),
    ("Să fii serios", "Să fii amuzant"),
    ("Să fii realist", "Să fii visător"),
    ("Să fii independent", "Să fii în echipă"),
    ("Să fii organizat", "Să fii creativ"),
    ("Să fii punctual", "Să fii relaxat"),
    ("Să ai ambiție mare", "Să ai viață liniștită"),
    ("Să fii competitiv", "Să fii relaxat"),
    ("Să ai control total", "Să fii liber"),
    ("Să fii disciplinat", "Să fii flexibil"),
    ("Să ai obiective clare", "Să explorezi liber"),
    ("Să fii lider bun", "Să fii prieten bun"),
    ("Să fii productiv", "Să fii relaxat"),
    ("Să fii perfecționist", "Să fii rapid"),
    ("Să fii stabil", "Să fii aventuros"),
    ("Să ai control asupra emoțiilor", "Să simți tot intens"),
    ("Să fii rațional", "Să fii emoțional"),
    ("Să ai succes singur", "Să ai succes în echipă"),
    ("Să fii discret", "Să fii expresiv"),
    ("Să fii calculat", "Să fii spontan"),
    ("Să fii constant", "Să fii imprevizibil"),
    ("Să fii focusat", "Să fii relaxat"),
    ("Să ai planuri clare", "Să mergi pe feeling"),
    ("Să fii sigur pe tine", "Să fii deschis la schimbare"),
    ("Să fii serios", "Să fii distractiv"),
    ("Să fii ambițios", "Să fii mulțumit"),
    ("Să fii organizat", "Să fii liber"),
    ("Să fii punctual", "Să fii chill"),
    ("Să ai obiective mari", "Să ai liniște"),
    ("Să fii competitiv", "Să fii cooperant"),
    ("Să fii lider", "Să fii follower"),
    ("Să fii rapid", "Să fii precis"),
    ("Să fii calm", "Să fii entuziast"),
    ("Să ai control", "Să ai libertate"),
    ("Să fii disciplinat", "Să fii relaxat"),
    ("Să fii serios", "Să fii amuzant"),
    ("Să fii realist", "Să fii visător"),
    ("Să fii logic", "Să fii creativ"),
]


class WouldYouRatherView(discord.ui.View):
    def __init__(self, option1: str, option2: str, duration: int = POLL_DURATION_SECONDS):
        super().__init__(timeout=duration)
        self.option1 = option1
        self.option2 = option2
        self.votes: Dict[int, int] = {}  # user_id -> 1 or 2
        self.message: Optional[discord.Message] = None
        self.finished = False

    async def update_message(self) -> None:
        if not self.message:
            return

        count1 = sum(1 for vote in self.votes.values() if vote == 1)
        count2 = sum(1 for vote in self.votes.values() if vote == 2)
        total = count1 + count2

        embed = discord.Embed(
            title="🤔 Ce ai alege dintre...",
            description=(
                f"**1.** {self.option1}\n"
                f"**2.** {self.option2}\n\n"
                f"⏳ Votarea este deschisă timp de **{POLL_DURATION_SECONDS} secunde**."
            ),
            color=discord.Color.blurple()
        )
        embed.add_field(name="Voturi curente", value=f"**{count1}** vs **{count2}**", inline=False)
        embed.set_footer(text=f"Total voturi: {total}")

        await self.message.edit(embed=embed, view=self)

    async def finish_poll(self) -> None:
        if self.finished:
            return

        self.finished = True
        for child in self.children:
            child.disabled = True

        count1 = sum(1 for vote in self.votes.values() if vote == 1)
        count2 = sum(1 for vote in self.votes.values() if vote == 2)
        total = count1 + count2

        if total == 0:
            percent1 = 0
            percent2 = 0
        else:
            percent1 = round((count1 / total) * 100)
            percent2 = round((count2 / total) * 100)

            # corectie ca sa dea exact 100
            diff = 100 - (percent1 + percent2)
            percent2 += diff

        embed = discord.Embed(
            title="📊 Rezultatul Would You Rather",
            description=(
                f"**Ce ai alege dintre...**\n\n"
                f"**1.** {self.option1}\n"
                f"**2.** {self.option2}"
            ),
            color=discord.Color.green()
        )

        embed.add_field(
            name="Rezultate finale",
            value=(
                f"**{self.option1}** — **{percent1}%** ({count1} voturi)\n"
                f"**{self.option2}** — **{percent2}%** ({count2} voturi)"
            ),
            inline=False
        )
        embed.set_footer(text=f"Total voturi: {total}")

        if self.message:
            await self.message.edit(embed=embed, view=self)

    async def on_timeout(self) -> None:
        await self.finish_poll()

    @discord.ui.button(label="Opțiunea 1", style=discord.ButtonStyle.primary)
    async def vote_option_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.finished:
            await interaction.response.send_message(
                "Sondajul s-a încheiat deja.",
                ephemeral=True
            )
            return

        self.votes[interaction.user.id] = 1
        await interaction.response.send_message(
            f"Ai votat pentru: **{self.option1}**",
            ephemeral=True
        )

    @discord.ui.button(label="Opțiunea 2", style=discord.ButtonStyle.secondary)
    async def vote_option_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.finished:
            await interaction.response.send_message(
                "Sondajul s-a încheiat deja.",
                ephemeral=True
            )
            return

        self.votes[interaction.user.id] = 2
        await interaction.response.send_message(
            f"Ai votat pentru: **{self.option2}**",
            ephemeral=True
        )


class WouldYouRather(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.current_poll_message_id: Optional[int] = None
        self.poll_lock = asyncio.Lock()
        self.auto_post_wyr.start()

    def cog_unload(self):
        self.auto_post_wyr.cancel()

    @tasks.loop(minutes=POST_INTERVAL_MINUTES)
    async def auto_post_wyr(self):
        async with self.poll_lock:
            channel = self.bot.get_channel(TARGET_CHANNEL_ID)
            if channel is None:
                try:
                    channel = await self.bot.fetch_channel(TARGET_CHANNEL_ID)
                except Exception as e:
                    print(f"[WouldYouRather] Nu pot lua canalul: {e}")
                    return

            if not isinstance(channel, discord.TextChannel):
                print("[WouldYouRather] Canalul nu este text channel.")
                return

            option1, option2 = random.choice(WOULD_YOU_RATHER_QUESTIONS)

            view = WouldYouRatherView(option1, option2, duration=POLL_DURATION_SECONDS)

            embed = discord.Embed(
                title="🤔 Ce ai alege dintre...",
                description=(
                    f"**1.** {option1}\n"
                    f"**2.** {option2}\n\n"
                    f"Apasă pe unul dintre butoane mai jos.\n"
                    f"Rezultatul apare în **{POLL_DURATION_SECONDS} secunde**."
                ),
                color=discord.Color.blurple()
            )
            embed.set_footer(text="Would You Rather")

            # schimbă label-ul butoanelor dinamic
            for child in view.children:
                if isinstance(child, discord.ui.Button):
                    if child.label == "Opțiunea 1":
                        child.label = option1[:80]
                    elif child.label == "Opțiunea 2":
                        child.label = option2[:80]

            try:
                message = await channel.send(embed=embed, view=view)
                view.message = message
                self.current_poll_message_id = message.id
            except Exception as e:
                print(f"[WouldYouRather] Eroare la trimiterea mesajului: {e}")
                return

            await asyncio.sleep(POLL_DURATION_SECONDS)
            await view.finish_poll()

    @auto_post_wyr.before_loop
    async def before_auto_post_wyr(self):
        await self.bot.wait_until_ready()

    @commands.command(name="testwyr")
    @commands.has_permissions(administrator=True)
    async def test_wyr(self, ctx: commands.Context):
        """
        Comandă de test pentru admini.
        """
        if ctx.channel.id != TARGET_CHANNEL_ID:
            await ctx.send(f"Folosește comanda doar pe canalul <#{TARGET_CHANNEL_ID}>.")
            return

        async with self.poll_lock:
            option1, option2 = random.choice(WOULD_YOU_RATHER_QUESTIONS)

            view = WouldYouRatherView(option1, option2, duration=POLL_DURATION_SECONDS)

            embed = discord.Embed(
                title="🤔 Ce ai alege dintre...",
                description=(
                    f"**1.** {option1}\n"
                    f"**2.** {option2}\n\n"
                    f"Apasă pe unul dintre butoane mai jos.\n"
                    f"Rezultatul apare în **{POLL_DURATION_SECONDS} secunde**."
                ),
                color=discord.Color.blurple()
            )
            embed.set_footer(text="Would You Rather - Test")

            for child in view.children:
                if isinstance(child, discord.ui.Button):
                    if child.label == "Opțiunea 1":
                        child.label = option1[:80]
                    elif child.label == "Opțiunea 2":
                        child.label = option2[:80]

            message = await ctx.send(embed=embed, view=view)
            view.message = message

            await asyncio.sleep(POLL_DURATION_SECONDS)
            await view.finish_poll()

    @test_wyr.error
    async def test_wyr_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Nu ai permisiunea să folosești această comandă.")
        else:
            await ctx.send("A apărut o eroare la rularea comenzii.")


async def setup(bot: commands.Bot):
    await bot.add_cog(WouldYouRather(bot))