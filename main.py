import asyncio
import os

import discord
from discord.ext import commands, tasks

from bot.core.config import get_discord_token, get_guild_id
from bot.db.session import init_db
from bot.services.points_reset_service import process_monthly_staff_points_reset
from bot.ui.panel_views import TicketPanelView
from bot.ui.ticket_views import TicketView


class RatoniiTicketsBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.message_content = False

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )

    async def setup_hook(self) -> None:
        await init_db()

        for filename in os.listdir("./bot/cogs"):
            if filename.endswith(".py") and not filename.startswith("_"):
                extension = f"bot.cogs.{filename[:-3]}"
                try:
                    await self.load_extension(extension)
                    print(f"[COG] Încărcat: {extension}")
                except Exception as exc:
                    print(f"[COG] Eroare la încărcarea {extension}: {type(exc).__name__}: {exc}")

        self.add_view(TicketPanelView(self))
        self.add_view(TicketView())

        guild_id = get_guild_id()

        try:
            if guild_id is not None:
                guild = discord.Object(id=guild_id)
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                print(f"[SYNC] S-au sincronizat {len(synced)} comenzi pe serverul {guild_id}.")
            else:
                synced = await self.tree.sync()
                print(f"[SYNC] S-au sincronizat {len(synced)} comenzi globale.")
        except Exception as exc:
            print(f"[SYNC] Eroare la sincronizare: {type(exc).__name__}: {exc}")

        if not self.monthly_points_reset_loop.is_running():
            self.monthly_points_reset_loop.start()

    async def on_ready(self) -> None:
        await self.change_presence(
            status=discord.Status.dnd,
            activity=discord.Game(name="mc.ratonii.ro")
        )
        print(f"[BOT] Conectat ca {self.user} (ID: {self.user.id})")

    @tasks.loop(hours=1)
    async def monthly_points_reset_loop(self) -> None:
        await process_monthly_staff_points_reset(self)

    @monthly_points_reset_loop.before_loop
    async def before_monthly_points_reset_loop(self) -> None:
        await self.wait_until_ready()


async def main() -> None:
    bot = RatoniiTicketsBot()
    token = get_discord_token()
    await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())