import asyncio
import os
import discord
from dotenv import load_dotenv

load_dotenv()

GUILD_ID = int(os.getenv("GUILD_ID", "0"))
MY_GUILD = discord.Object(id=GUILD_ID) 

SHOCKULETZ_USER_ID = 237212746763075585  

from discord.ext import commands, tasks

from bot.core.config import get_discord_token
from bot.db.session import init_db
from bot.services.points_reset_service import process_monthly_staff_points_reset
from bot.ui.panel_views import TicketPanelView
from bot.ui.ticket_views import TicketView

class RatoniiTicketsBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.message_content = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )

    async def setup_hook(self) -> None:
        await init_db()
        print("[DB] Database initialized.")

        for filename in os.listdir("./bot/cogs"):
            if filename.endswith(".py") and not filename.startswith("_"):
                extension = f"bot.cogs.{filename[:-3]}"
                try:
                    await self.load_extension(extension)
                    print(f"[COG] Loaded: {extension}")
                except Exception as exc:
                    print(f"[COG] Failed to load {extension}: {type(exc).__name__}: {exc}")
        
        try:
            guild = discord.Object(id=GUILD_ID)
            synced = await self.tree.sync(guild=guild)
            print(f"Synced {len(synced)} guild command(s) to {GUILD_ID}.")
        except Exception as e:
            print(f"Sync error: {type(e).__name__}: {e}")

        self.add_view(TicketPanelView(self))
        self.add_view(TicketView())
        print("[VIEW] Persistent views loaded.")

        if not self.monthly_points_reset_loop.is_running():
            self.monthly_points_reset_loop.start()
            print("[TASK] Monthly points reset loop started.")

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.author.id == SHOCKULETZ_USER_ID:
            content = message.content.lower()

            if self.user in message.mentions and "te iubi" in content:
                await message.reply("si eu te iubesc <3")
            elif self.user in message.mentions and "asa e?" in content:
                await message.reply("da, asa e")

        await self.process_commands(message)

    async def on_ready(self) -> None:
        await self.change_presence(
            status=discord.Status.dnd,
            activity=discord.Game(name="mc.ratonii.ro")
        )
        print(f"[BOT] Connected as {self.user} (ID: {self.user.id})")

    @tasks.loop(hours=1)
    async def monthly_points_reset_loop(self) -> None:
        try:
            await process_monthly_staff_points_reset(self)
        except Exception as exc:
            print(f"[TASK] Error in monthly_points_reset_loop: {type(exc).__name__}: {exc}")

    @monthly_points_reset_loop.before_loop
    async def before_monthly_points_reset_loop(self) -> None:
        await self.wait_until_ready()


bot = RatoniiTicketsBot()


@bot.command(name="syncguild")
@commands.is_owner()
async def syncguild_command(ctx: commands.Context) -> None:
    try:
        guild = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync(guild=guild)
        await ctx.send(f"✅ Synced {len(synced)} guild command(s) to {GUILD_ID}.")
    except Exception as exc:
        await ctx.send(f"❌ Sync error: {type(exc).__name__}: {exc}")

@bot.command(name="load")
@commands.is_owner()
async def load_command(ctx: commands.Context, extension: str) -> None:
    try:
        await bot.load_extension(extension)
        guild = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync(guild=guild)
        await ctx.send(f"✅ Loaded {extension} și am sincronizat {len(synced)} command(s).")
    except Exception as exc:
        await ctx.send(f"❌ Load error: {type(exc).__name__}: {exc}")


@bot.command(name="reload")
@commands.is_owner()
async def reload_command(ctx: commands.Context, extension: str) -> None:
    try:
        await bot.reload_extension(extension)
        guild = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync(guild=guild)
        await ctx.send(f"✅ Reloaded {extension} și am sincronizat {len(synced)} command(s).")
    except Exception as exc:
        await ctx.send(f"❌ Reload error: {type(exc).__name__}: {exc}")

@bot.command(name="resetappcmds")
@commands.is_owner()
async def resetappcmds_command(ctx: commands.Context) -> None:
    try:
        guild = discord.Object(id=GUILD_ID)

        # sterge toate comenzile globale vechi
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()

        # sterge toate comenzile vechi de pe guild
        bot.tree.clear_commands(guild=guild)
        await bot.tree.sync(guild=guild)

        await ctx.send("✅ Am șters toate application commands globale și de pe guild. Dă restart la bot acum.")
    except Exception as exc:
        await ctx.send(f"❌ Error: {type(exc).__name__}: {exc}")

async def main() -> None:
    token = get_discord_token()
    await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())