import asyncio
import os
import discord
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

from discord.ext import commands, tasks

from bot.core.config import get_discord_token
from bot.db.session import init_db
from bot.services.points_reset_service import process_monthly_staff_points_reset
from bot.ui.panel_views import TicketPanelView
from bot.ui.ticket_views import TicketView

TARGET_CHANNEL_ID = 1482810897167679578  # pune ID-ul canalului
HF_TOKEN = os.getenv("HF_TOKEN")
HF_MODEL = os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")

client_ai = OpenAI(
    api_key=HF_TOKEN,
    base_url="https://router.huggingface.co/v1"
)

def split_message(text: str, chunk_size: int = 1900):
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


def looks_cut_off(text: str) -> bool:
    text = text.strip()
    if not text:
        return False

    good_endings = (".", "!", "?", "”", "\"", "`", "…")
    if text.endswith(good_endings):
        return False

    return True


async def generate_full_reply(user_msg: str) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a friendly Romanian Discord bot. "
                "Reply in Romanian, clearly and naturally. "
                "Keep answers short and complete, maximum 3-4 sentences. "
                "Never cut off mid-sentence."
            )
        },
        {
            "role": "user",
            "content": user_msg
        }
    ]

    full_reply = ""

    for _ in range(3):  # maxim 3 încercări
        response = client_ai.chat.completions.create(
            model=HF_MODEL,
            messages=messages,
            max_tokens=300
        )

        part = response.choices[0].message.content or ""
        part = part.strip()

        if not part:
            break

        if full_reply:
            full_reply += " " + part
        else:
            full_reply = part

        if not looks_cut_off(full_reply):
            break

        messages.append({"role": "assistant", "content": part})
        messages.append({
            "role": "user",
            "content": "Continuă exact de unde ai rămas și termină propoziția scurt."
        })

    return full_reply.strip()

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

        self.add_view(TicketPanelView(self))
        self.add_view(TicketView())
        print("[VIEW] Persistent views loaded.")

        if not self.monthly_points_reset_loop.is_running():
            self.monthly_points_reset_loop.start()
            print("[TASK] Monthly points reset loop started.")

    async def on_ready(self) -> None:
        await self.change_presence(
            status=discord.Status.dnd,
            activity=discord.Game(name="mc.ratonii.ro")
        )
        print(f"[BOT] Connected as {self.user} (ID: {self.user.id})")

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        if self.user is not None and message.channel.id == TARGET_CHANNEL_ID and self.user in message.mentions:
            user_msg = message.content
            user_msg = user_msg.replace(f"<@{self.user.id}>", "")
            user_msg = user_msg.replace(f"<@!{self.user.id}>", "")
            user_msg = user_msg.strip()

            if not user_msg:
                await message.reply("Scrie ceva după mention 😄")
                return

            try:
                async with message.channel.typing():
                    reply = await generate_full_reply(user_msg)

                if not reply:
                    await message.reply("N-am putut genera un răspuns.")
                    return

                for i, chunk in enumerate(split_message(reply)):
                    if i == 0:
                        await message.reply(chunk)
                    else:
                        await message.channel.send(chunk)

            except Exception as e:
                print(f"[AI] Error: {type(e).__name__}: {e}")
                await message.reply("Eroare la AI 😢")

        await self.process_commands(message)

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


@bot.command(name="sync")
@commands.is_owner()
async def sync_command(ctx: commands.Context) -> None:
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"✅ Synced {len(synced)} global command(s).")
    except Exception as exc:
        await ctx.send(f"❌ Sync error: {type(exc).__name__}: {exc}")


async def main() -> None:
    token = get_discord_token()
    await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())