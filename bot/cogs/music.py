import asyncio

import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp


ALLOWED_CHANNEL_IDS = {
    1088801768051327056,
    1272661493758034051,
}

ALLOWED_ROLE_IDS = {
    1370492194284376213,
    1370492197677301871,
    1370492200718172210,
    1092889216825962506,
    1301254665186312324,
}

ADMIN_ROLE_IDS = {
    1111880505441402892,
    1189296642164260904,
    1470127170251788349,
    1129501329740533883,
    1093217111876325406,
}

AUTO_DISCONNECT_SECONDS = 30


class YTDLLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)


YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "extract_flat": False,
    "logger": YTDLLogger(),
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


def spotify_embed(
    *,
    title: str,
    description: str,
    thumbnail: str | None = None,
    url: str | None = None,
    footer: str = "Ratonii Music",
) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=0x1DB954,
    )

    if url:
        embed.url = url

    if thumbnail:
        embed.set_thumbnail(url=thumbnail)

    embed.set_footer(text=footer)
    return embed


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)
        self.queues: dict[int, list[dict]] = {}
        self.now_playing: dict[int, dict] = {}
        self.disconnect_tasks: dict[int, asyncio.Task] = {}

    def user_has_allowed_role(self, member: discord.Member) -> bool:
        return any(role.id in ALLOWED_ROLE_IDS for role in member.roles)

    def user_has_admin_role(self, member: discord.Member) -> bool:
        return any(role.id in ADMIN_ROLE_IDS for role in member.roles)

    async def check_access(
        self,
        interaction: discord.Interaction,
        *,
        admin_only: bool = False,
    ) -> bool:
        if not interaction.guild:
            if interaction.response.is_done():
                await interaction.edit_original_response(
                    content="Comanda merge doar pe server.",
                    embed=None
                )
            else:
                await interaction.response.send_message(
                    "Comanda merge doar pe server.",
                    ephemeral=True
                )
            return False

        if not isinstance(interaction.user, discord.Member):
            if interaction.response.is_done():
                await interaction.edit_original_response(
                    content="User invalid.",
                    embed=None
                )
            else:
                await interaction.response.send_message(
                    "User invalid.",
                    ephemeral=True
                )
            return False

        if interaction.channel_id not in ALLOWED_CHANNEL_IDS:
            channels = ", ".join(f"<#{cid}>" for cid in ALLOWED_CHANNEL_IDS)

            if interaction.response.is_done():
                await interaction.edit_original_response(
                    content=f"Aceste comenzi merg doar pe {channels}.",
                    embed=None
                )
            else:
                await interaction.response.send_message(
                    f"Aceste comenzi merg doar pe {channels}.",
                    ephemeral=True
                )
            return False

        if admin_only:
            if not self.user_has_admin_role(interaction.user):
                if interaction.response.is_done():
                    await interaction.edit_original_response(
                        content="Nu ai permisiunea sa folosesti aceasta comanda.",
                        embed=None
                    )
                else:
                    await interaction.response.send_message(
                        "Nu ai permisiunea sa folosesti aceasta comanda.",
                        ephemeral=True
                    )
                return False
        else:
            if not self.user_has_allowed_role(interaction.user):
                if interaction.response.is_done():
                    await interaction.edit_original_response(
                        content="Nu ai rolul necesar pentru aceasta comanda.",
                        embed=None
                    )
                else:
                    await interaction.response.send_message(
                        "Nu ai rolul necesar pentru aceasta comanda.",
                        ephemeral=True
                    )
                return False

        return True

    async def check_voice_access(self, interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            if interaction.response.is_done():
                await interaction.edit_original_response(
                    content="Comanda merge doar pe server.",
                    embed=None
                )
            else:
                await interaction.response.send_message(
                    "Comanda merge doar pe server.",
                    ephemeral=True
                )
            return False

        if not isinstance(interaction.user, discord.Member):
            if interaction.response.is_done():
                await interaction.edit_original_response(
                    content="User invalid.",
                    embed=None
                )
            else:
                await interaction.response.send_message(
                    "User invalid.",
                    ephemeral=True
                )
            return False

        if not interaction.user.voice or not interaction.user.voice.channel:
            if interaction.response.is_done():
                await interaction.edit_original_response(
                    content="Trebuie sa fii pe un voice channel.",
                    embed=None
                )
            else:
                await interaction.response.send_message(
                    "Trebuie sa fii pe un voice channel.",
                    ephemeral=True
                )
            return False

        vc = interaction.guild.voice_client
        if vc and vc.channel and interaction.user.voice.channel != vc.channel:
            if interaction.response.is_done():
                await interaction.edit_original_response(
                    content=f"Trebuie sa fii pe acelasi voice channel cu botul: **{vc.channel.name}**.",
                    embed=None
                )
            else:
                await interaction.response.send_message(
                    f"Trebuie sa fii pe acelasi voice channel cu botul: **{vc.channel.name}**.",
                    ephemeral=True
                )
            return False

        return True

    def get_guild_queue(self, guild_id: int) -> list[dict]:
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]

    def cancel_disconnect(self, guild_id: int):
        task = self.disconnect_tasks.get(guild_id)
        if task:
            task.cancel()
            self.disconnect_tasks.pop(guild_id, None)

    async def schedule_disconnect(self, guild: discord.Guild):
        guild_id = guild.id

        if guild_id in self.disconnect_tasks:
            return

        async def task():
            try:
                await asyncio.sleep(AUTO_DISCONNECT_SECONDS)

                vc = guild.voice_client
                queue = self.get_guild_queue(guild_id)

                if vc and not vc.is_playing() and not vc.is_paused() and not queue:
                    print(f"[AUTO DISCONNECT] {guild.name}")
                    await vc.disconnect(force=True)
                    self.now_playing.pop(guild_id, None)

            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"[AUTO DISCONNECT ERROR] {type(e).__name__}: {e}")
            finally:
                self.disconnect_tasks.pop(guild_id, None)

        self.disconnect_tasks[guild_id] = asyncio.create_task(task())

    async def extract_info(self, query: str) -> dict:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.ytdl.extract_info(query, download=False)
        )

    async def ensure_voice(self, interaction: discord.Interaction) -> discord.VoiceClient | None:
        if not interaction.guild:
            return None

        if not isinstance(interaction.user, discord.Member):
            return None

        if not interaction.user.voice or not interaction.user.voice.channel:
            return None

        channel = interaction.user.voice.channel
        vc = interaction.guild.voice_client

        if vc is None:
            vc = await channel.connect()
        elif vc.channel != channel:
            return None

        return vc

    def normalize_data(self, data: dict) -> dict:
        if "entries" in data:
            entries = data.get("entries") or []
            if not entries:
                raise ValueError("Nu am gasit nicio piesa.")
            data = entries[0]

        title = data.get("title", "Necunoscut")
        webpage_url = data.get("webpage_url") or data.get("original_url") or data.get("url")
        thumbnail = data.get("thumbnail")
        uploader = data.get("uploader", "Necunoscut")
        duration = data.get("duration")

        duration_text = "Live"
        if isinstance(duration, int):
            minutes = duration // 60
            seconds = duration % 60
            duration_text = f"{minutes}:{seconds:02d}"

        return {
            "title": title,
            "webpage_url": webpage_url,
            "thumbnail": thumbnail,
            "uploader": uploader,
            "duration_text": duration_text,
        }

    async def refresh_song_stream(self, song: dict) -> dict:
        source_query = song.get("webpage_url") or song.get("search_query")
        if not source_query:
            raise ValueError("Melodia nu are sursa valida pentru refresh.")

        fresh_data = await self.extract_info(source_query)

        if "entries" in fresh_data:
            entries = fresh_data.get("entries") or []
            if not entries:
                raise ValueError("Nu am putut reobtine melodia din queue.")
            fresh_data = entries[0]

        stream_url = fresh_data.get("url")
        if not stream_url:
            raise ValueError("Nu am putut obtine stream URL.")

        song["stream_url"] = stream_url
        song["webpage_url"] = (
            fresh_data.get("webpage_url")
            or song.get("webpage_url")
            or source_query
        )
        song["thumbnail"] = fresh_data.get("thumbnail") or song.get("thumbnail")
        song["uploader"] = fresh_data.get("uploader") or song.get("uploader", "Necunoscut")

        duration = fresh_data.get("duration")
        if isinstance(duration, int):
            minutes = duration // 60
            seconds = duration % 60
            song["duration_text"] = f"{minutes}:{seconds:02d}"

        return song

    def make_after_callback(self, guild: discord.Guild):
        def after_play(error):
            if error:
                print(f"[AFTER PLAY ERROR] {error}")

            self.bot.loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self.play_next(guild))
            )

        return after_play

    async def play_next(self, guild: discord.Guild):
        vc = guild.voice_client
        if vc is None:
            return

        queue = self.get_guild_queue(guild.id)

        if not queue:
            self.now_playing.pop(guild.id, None)
            await self.schedule_disconnect(guild)
            return

        self.cancel_disconnect(guild.id)

        song = queue.pop(0)

        try:
            song = await self.refresh_song_stream(song)
            self.now_playing[guild.id] = song

            source = discord.FFmpegPCMAudio(song["stream_url"], **FFMPEG_OPTIONS)
            vc.play(source, after=self.make_after_callback(guild))

        except Exception as e:
            print(f"[PLAY NEXT ERROR] {type(e).__name__}: {e}")
            await self.play_next(guild)
            return

        channel = guild.get_channel(song["text_channel_id"])
        if isinstance(channel, discord.TextChannel):
            duration_text = song.get("duration_text", "Necunoscut")

            desc = (
                f"**[{song['title']}]({song['webpage_url']})**\n\n"
                f"👤 **Artist/Uploader:** {song['uploader']}\n"
                f"⏱️ **Durata:** {duration_text}\n"
                f"🔊 **Canal:** {vc.channel.name}"
            )

            embed = spotify_embed(
                title="🎵 Now Playing",
                description=desc,
                thumbnail=song.get("thumbnail"),
                url=song["webpage_url"],
                footer=f"Cerut de {song['requested_by']}"
            )

            try:
                await channel.send(embed=embed)
            except Exception as e:
                print(f"[NOW PLAYING SEND ERROR] {type(e).__name__}: {e}")

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if not member.guild:
            return

        vc = member.guild.voice_client
        if vc is None or vc.channel is None:
            return

        if self.bot.user and member.id == self.bot.user.id:
            if after.channel is not None:
                self.cancel_disconnect(member.guild.id)
            else:
                self.cancel_disconnect(member.guild.id)
                self.now_playing.pop(member.guild.id, None)
            return

        members_without_bots = [m for m in vc.channel.members if not m.bot]
        if len(members_without_bots) == 0:
            try:
                self.get_guild_queue(member.guild.id).clear()
                self.now_playing.pop(member.guild.id, None)
                self.cancel_disconnect(member.guild.id)
                await vc.disconnect(force=True)
                print(f"[AUTO LEAVE ALONE] {member.guild.name}")
            except Exception as e:
                print(f"[AUTO LEAVE ALONE ERROR] {type(e).__name__}: {e}")

    @app_commands.command(name="join", description="Intra pe voice channel-ul tau.")
    async def join(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_message("Ma conectez...", ephemeral=True)

            if not await self.check_access(interaction):
                return

            if not await self.check_voice_access(interaction):
                return

            channel = interaction.user.voice.channel
            vc = interaction.guild.voice_client

            if vc is None:
                await channel.connect()
            elif vc.channel != channel:
                await interaction.edit_original_response(
                    content=f"Botul este deja pe **{vc.channel.name}**.",
                    embed=None
                )
                return

            self.cancel_disconnect(interaction.guild.id)

            embed = spotify_embed(
                title="🎧 Connected",
                description=f"M-am conectat pe **{channel.name}**.",
                footer=f"Cerut de {interaction.user.display_name}"
            )
            await interaction.edit_original_response(content="", embed=embed)

        except Exception as e:
            print(f"[JOIN ERROR] {type(e).__name__}: {e}")
            try:
                await interaction.edit_original_response(
                    content=f"Eroare: `{type(e).__name__}: {e}`",
                    embed=None
                )
            except Exception:
                pass

    @app_commands.command(name="play", description="Reda muzica sau o adauga in queue.")
    @app_commands.describe(query="Link YouTube sau numele piesei")
    async def play(self, interaction: discord.Interaction, query: str):
        try:
            loading = spotify_embed(
                title="🔎 Searching",
                description=f"Caut pentru: **{query}**",
                footer=f"Cerut de {interaction.user.display_name}"
            )
            await interaction.response.send_message(embed=loading)

            if not await self.check_access(interaction):
                return

            if not await self.check_voice_access(interaction):
                return

            vc = await self.ensure_voice(interaction)
            if vc is None:
                if interaction.guild.voice_client and interaction.guild.voice_client.channel:
                    await interaction.edit_original_response(
                        content=f"Botul este deja pe **{interaction.guild.voice_client.channel.name}**.",
                        embed=None
                    )
                else:
                    await interaction.edit_original_response(
                        content="Nu m-am putut conecta pe voice.",
                        embed=None
                    )
                return

            self.cancel_disconnect(interaction.guild.id)

            data = await self.extract_info(query)
            info = self.normalize_data(data)

            song = {
                "title": info["title"],
                "webpage_url": info["webpage_url"],
                "thumbnail": info["thumbnail"],
                "uploader": info["uploader"],
                "duration_text": info["duration_text"],
                "requested_by": interaction.user.display_name,
                "text_channel_id": interaction.channel_id,
                "search_query": info["webpage_url"] or query,
            }

            queue = self.get_guild_queue(interaction.guild.id)

            if vc.is_playing() or vc.is_paused():
                queue.append(song)

                embed = spotify_embed(
                    title="➕ Added to Queue",
                    description=(
                        f"**[{song['title']}]({song['webpage_url']})**\n\n"
                        f"👤 **Artist/Uploader:** {song['uploader']}\n"
                        f"⏱️ **Durata:** {song['duration_text']}\n"
                        f"📜 **Pozitie in queue:** {len(queue)}"
                    ),
                    thumbnail=song["thumbnail"],
                    url=song["webpage_url"],
                    footer=f"Adaugat de {interaction.user.display_name}"
                )
                await interaction.edit_original_response(content="", embed=embed)
                return

            song = await self.refresh_song_stream(song)
            self.now_playing[interaction.guild.id] = song

            source = discord.FFmpegPCMAudio(song["stream_url"], **FFMPEG_OPTIONS)
            vc.play(source, after=self.make_after_callback(interaction.guild))
            self.cancel_disconnect(interaction.guild.id)

            desc = (
                f"**[{song['title']}]({song['webpage_url']})**\n\n"
                f"👤 **Artist/Uploader:** {song['uploader']}\n"
                f"⏱️ **Durata:** {song['duration_text']}\n"
                f"🔊 **Canal:** {vc.channel.name}"
            )

            embed = spotify_embed(
                title="🎵 Now Playing",
                description=desc,
                thumbnail=song["thumbnail"],
                url=song["webpage_url"],
                footer=f"Cerut de {interaction.user.display_name}"
            )

            await interaction.edit_original_response(content="", embed=embed)

        except Exception as e:
            print(f"[PLAY ERROR] {type(e).__name__}: {e}")
            try:
                await interaction.edit_original_response(
                    content=f"Eroare: `{type(e).__name__}: {e}`",
                    embed=None
                )
            except Exception:
                pass

    @app_commands.command(name="queue", description="Arata queue-ul curent.")
    async def queue_cmd(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_message("Procesez...", ephemeral=True)

            if not await self.check_access(interaction):
                return

            if not await self.check_voice_access(interaction):
                return

            queue = self.get_guild_queue(interaction.guild.id)
            now = self.now_playing.get(interaction.guild.id)

            desc_parts = []

            if now:
                desc_parts.append(
                    f"🎵 **Now Playing:**\n"
                    f"**[{now['title']}]({now['webpage_url']})**\n"
                    f"👤 {now['uploader']} | ⏱️ {now['duration_text']}\n"
                )

            if queue:
                lines = []
                for index, song in enumerate(queue[:10], start=1):
                    lines.append(
                        f"`{index}.` **[{song['title']}]({song['webpage_url']})** - {song['requested_by']}"
                    )
                desc_parts.append("📜 **Queue:**\n" + "\n".join(lines))

                if len(queue) > 10:
                    desc_parts.append(f"\n... si inca **{len(queue) - 10}** piese.")
            else:
                if not now:
                    desc_parts.append("Nu exista nimic in queue.")
                else:
                    desc_parts.append("Nu mai exista alte piese in queue.")

            embed = spotify_embed(
                title="📋 Music Queue",
                description="\n\n".join(desc_parts),
                footer=f"Cerut de {interaction.user.display_name}"
            )
            await interaction.edit_original_response(content="", embed=embed)

        except Exception as e:
            print(f"[QUEUE ERROR] {type(e).__name__}: {e}")

    @app_commands.command(name="pause", description="Pune muzica pe pauza.")
    async def pause(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_message("Procesez...", ephemeral=True)

            if not await self.check_access(interaction):
                return

            if not await self.check_voice_access(interaction):
                return

            if not interaction.guild or not interaction.guild.voice_client:
                await interaction.edit_original_response(content="Nu sunt conectat pe voice.", embed=None)
                return

            vc = interaction.guild.voice_client

            if vc.is_playing():
                vc.pause()

                embed = spotify_embed(
                    title="⏸️ Paused",
                    description="Melodia curenta a fost pusa pe pauza.",
                    footer=f"Cerut de {interaction.user.display_name}"
                )
                await interaction.edit_original_response(content="", embed=embed)
            else:
                await interaction.edit_original_response(content="Nu redau nimic acum.", embed=None)

        except Exception as e:
            print(f"[PAUSE ERROR] {type(e).__name__}: {e}")

    @app_commands.command(name="resume", description="Reia muzica.")
    async def resume(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_message("Procesez...", ephemeral=True)

            if not await self.check_access(interaction):
                return

            if not await self.check_voice_access(interaction):
                return

            if not interaction.guild or not interaction.guild.voice_client:
                await interaction.edit_original_response(content="Nu sunt conectat pe voice.", embed=None)
                return

            vc = interaction.guild.voice_client

            if vc.is_paused():
                vc.resume()
                self.cancel_disconnect(interaction.guild.id)

                embed = spotify_embed(
                    title="▶️ Resumed",
                    description="Melodia curenta a fost reluata.",
                    footer=f"Cerut de {interaction.user.display_name}"
                )
                await interaction.edit_original_response(content="", embed=embed)
            else:
                await interaction.edit_original_response(content="Nu am nimic pus pe pauza.", embed=None)

        except Exception as e:
            print(f"[RESUME ERROR] {type(e).__name__}: {e}")

    @app_commands.command(name="stop", description="Opreste muzica si goleste queue-ul.")
    async def stop(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_message("Procesez...", ephemeral=True)

            if not await self.check_access(interaction):
                return

            if not await self.check_voice_access(interaction):
                return

            if not interaction.guild or not interaction.guild.voice_client:
                await interaction.edit_original_response(
                    content="Nu sunt conectat pe voice.",
                    embed=None
                )
                return

            vc = interaction.guild.voice_client
            self.get_guild_queue(interaction.guild.id).clear()
            self.now_playing.pop(interaction.guild.id, None)

            if vc.is_playing() or vc.is_paused():
                vc.stop()

            await self.schedule_disconnect(interaction.guild)

            embed = spotify_embed(
                title="⏹️ Stopped",
                description=f"Am oprit muzica si am golit queue-ul. Daca nu pornește nimic in {AUTO_DISCONNECT_SECONDS} secunde, botul va iesi singur.",
                footer=f"Cerut de {interaction.user.display_name}"
            )
            await interaction.edit_original_response(content="", embed=embed)

        except Exception as e:
            print(f"[STOP ERROR] {type(e).__name__}: {e}")

    @app_commands.command(name="leave", description="Iese de pe voice si goleste queue-ul.")
    async def leave(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_message("Ies de pe voice...", ephemeral=True)

            if not await self.check_access(interaction):
                return

            if not await self.check_voice_access(interaction):
                return

            if not interaction.guild or not interaction.guild.voice_client:
                await interaction.edit_original_response(
                    content="Nu sunt conectat pe voice.",
                    embed=None
                )
                return

            channel_name = interaction.guild.voice_client.channel.name
            self.get_guild_queue(interaction.guild.id).clear()
            self.now_playing.pop(interaction.guild.id, None)
            self.cancel_disconnect(interaction.guild.id)

            await interaction.guild.voice_client.disconnect(force=True)

            embed = spotify_embed(
                title="👋 Disconnected",
                description=f"Am iesit de pe **{channel_name}** si am golit queue-ul.",
                footer=f"Cerut de {interaction.user.display_name}"
            )
            await interaction.edit_original_response(content="", embed=embed)

        except Exception as e:
            print(f"[LEAVE ERROR] {type(e).__name__}: {e}")

    @app_commands.command(name="skip", description="Da skip la piesa curenta.")
    async def skip(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_message("Dau skip...", ephemeral=True)

            if not await self.check_access(interaction):
                return

            if not await self.check_voice_access(interaction):
                return

            if not interaction.guild or not interaction.guild.voice_client:
                await interaction.edit_original_response(
                    content="Nu sunt conectat pe voice.",
                    embed=None
                )
                return

            vc = interaction.guild.voice_client

            if vc.is_playing() or vc.is_paused():
                vc.stop()

                embed = spotify_embed(
                    title="⏭️ Skipped",
                    description="Am dat skip la piesa curenta.",
                    footer=f"Cerut de {interaction.user.display_name}"
                )
                await interaction.edit_original_response(content="", embed=embed)
            else:
                await interaction.edit_original_response(
                    content="Nu redau nimic.",
                    embed=None
                )

        except Exception as e:
            print(f"[SKIP ERROR] {type(e).__name__}: {e}")

    @app_commands.command(name="remove", description="Scoate o piesa din queue dupa pozitie.")
    @app_commands.describe(position="Pozitia piesei din /queue")
    async def remove(self, interaction: discord.Interaction, position: int):
        try:
            await interaction.response.send_message("Procesez...", ephemeral=True)

            if not await self.check_access(interaction, admin_only=True):
                return

            if not await self.check_voice_access(interaction):
                return

            queue = self.get_guild_queue(interaction.guild.id)

            if not queue:
                await interaction.edit_original_response(content="Queue-ul este gol.", embed=None)
                return

            if position < 1 or position > len(queue):
                await interaction.edit_original_response(
                    content=f"Pozitie invalida. Alege intre 1 si {len(queue)}.",
                    embed=None
                )
                return

            removed_song = queue.pop(position - 1)

            embed = spotify_embed(
                title="🗑️ Removed from Queue",
                description=(
                    f"Am scos din queue:\n"
                    f"**[{removed_song['title']}]({removed_song['webpage_url']})**\n\n"
                    f"📜 **Pozitie stearsa:** {position}"
                ),
                thumbnail=removed_song.get("thumbnail"),
                url=removed_song["webpage_url"],
                footer=f"Scos de {interaction.user.display_name}"
            )
            await interaction.edit_original_response(content="", embed=embed)

        except Exception as e:
            print(f"[REMOVE ERROR] {type(e).__name__}: {e}")

    @app_commands.command(name="clearqueue", description="Goleste queue-ul.")
    async def clearqueue(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_message("Procesez...", ephemeral=True)

            if not await self.check_access(interaction, admin_only=True):
                return

            if not await self.check_voice_access(interaction):
                return

            queue = self.get_guild_queue(interaction.guild.id)

            if not queue:
                await interaction.edit_original_response(content="Queue-ul este deja gol.", embed=None)
                return

            cleared_count = len(queue)
            queue.clear()

            embed = spotify_embed(
                title="🧹 Queue Cleared",
                description=f"Am sters **{cleared_count}** piese din queue.",
                footer=f"Golita de {interaction.user.display_name}"
            )
            await interaction.edit_original_response(content="", embed=embed)

        except Exception as e:
            print(f"[CLEARQUEUE ERROR] {type(e).__name__}: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))