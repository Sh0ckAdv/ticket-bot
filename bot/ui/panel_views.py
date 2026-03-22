import discord
from sqlalchemy import select

from bot.db.models import GuildSettings, Ticket, TicketBlacklist
from bot.db.session import AsyncSessionLocal
from bot.ui.ticket_views import TicketView


class TicketPanelView(discord.ui.View):
    def __init__(self, bot: discord.Client | None = None) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    async def ask_question(
        self,
        channel: discord.TextChannel,
        user: discord.Member,
        question: str,
        timeout: int = 300,
    ) -> discord.Message | None:
        await channel.send(f"{user.mention} {question}")

        def check(message: discord.Message) -> bool:
            return (
                message.channel.id == channel.id
                and message.author.id == user.id
            )

        try:
            message = await channel.guild._state._get_client().wait_for(
                "message",
                timeout=timeout,
                check=check,
            )
            return message
        except Exception:
            await channel.send(
                f"{user.mention} Ai depășit timpul de răspuns. Închide ticketul și deschide unul nou dacă mai ai nevoie."
            )
            return None

    async def start_password_questions(
        self,
        channel: discord.TextChannel,
        user: discord.Member,
    ) -> None:
        q1 = await self.ask_question(
            channel,
            user,
            "Salut, care e numele contului?",
        )
        if q1 is None:
            return

        q2 = await self.ask_question(
            channel,
            user,
            "Contul este **Premium** sau **Non-Premium**?",
        )
        if q2 is None:
            return

        q3 = await self.ask_question(
            channel,
            user,
            "Ai un email asociat contului? **(Da/Nu)**?",
        )
        if q3 is None:
            return

        q4 = await self.ask_question(
            channel,
            user,
            "Ai dovezi? Dacă da, atașează-le acum.",
        )
        if q4 is None:
            return

        info_embed = discord.Embed(
            title="Acum așteaptă un răspuns de la staff",
            description=(
                "**Informații utile:**\n"
                "Dacă nu ai dovezi, urmează acești pași:\n"
                "• Creează un cont secundar\n"
                "• Intră pe o secțiune (ex: Earth)\n"
                "• Scrie în chat: `resetare parola ratonii`\n"
                "• Apasă Enter\n"
                "• Fă screenshot fullscreen\n"
                "• Trimite poza aici\n\n"
                "**Asigură-te că screenshot-ul:**\n"
                "✔️ este clar\n"
                "✔️ se vede tot ecranul\n"
                "✔️ nu este decupat"
            ),
            color=discord.Color.blurple(),
        )
        info_embed.set_footer(text="Ratonii Tickets")
        await channel.send(embed=info_embed)

    async def create_ticket(
        self,
        interaction: discord.Interaction,
        ticket_type: str,
    ) -> None:
        if interaction.guild is None:
            return

        guild = interaction.guild
        user = interaction.user

        await interaction.response.defer(ephemeral=True)

        async with AsyncSessionLocal() as session:
            settings_result = await session.execute(
                select(GuildSettings).where(GuildSettings.guild_id == guild.id)
            )
            settings = settings_result.scalar_one_or_none()

            if settings is None:
                await interaction.followup.send(
                    "Sistemul de tickete nu este configurat.",
                    ephemeral=True,
                )
                return

            blacklist_result = await session.execute(
                select(TicketBlacklist).where(
                    TicketBlacklist.guild_id == guild.id,
                    TicketBlacklist.user_id == user.id,
                )
            )
            blacklist_entry = blacklist_result.scalar_one_or_none()

            if blacklist_entry is not None:
                embed = discord.Embed(
                    title="Nu poți deschide tickete",
                    description="Ai fost adăugat în blacklist-ul sistemului de tickete.",
                    color=discord.Color.red(),
                )
                embed.add_field(
                    name="Motiv",
                    value=blacklist_entry.reason,
                    inline=False,
                )
                embed.set_footer(text="Ratonii Tickets")

                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            open_tickets_result = await session.execute(
                select(Ticket).where(
                    Ticket.guild_id == guild.id,
                    Ticket.creator_id == user.id,
                    Ticket.status == "open",
                )
            )
            open_tickets = open_tickets_result.scalars().all()

            if len(open_tickets) >= settings.max_open_tickets_per_user:
                await interaction.followup.send(
                    "Ai deja numărul maxim de tickete deschise.",
                    ephemeral=True,
                )
                return

            count_result = await session.execute(select(Ticket))
            ticket_count = len(count_result.scalars().all()) + 1

            if ticket_type == "password":
                channel_name = f"🔐-parola-{ticket_count:04d}"
                allowed_role_ids = [settings.password_support_role_id]
                category_label = "Recuperare Parolă"
                category_emoji = "🔐"
                description_text = "Răspunde la întrebările de mai jos pentru ca staff-ul să te poată ajuta mai rapid."
            elif ticket_type == "unban":
                channel_name = f"🔨-unban-{ticket_count:04d}"
                allowed_role_ids = [
                    settings.discord_staff_role_id,
                    settings.manager_discord_role_id,
                ]
                category_label = "Cerere Unban"
                category_emoji = "🔨"
                description_text = "Te rugăm să explici de ce consideri că sancțiunea ar trebui revizuită."
            else:
                channel_name = f"🎫-ticket-{ticket_count:04d}"
                allowed_role_ids = [
                    settings.discord_staff_role_id,
                    settings.manager_discord_role_id,
                ]
                category_label = "Ticket"
                category_emoji = "🎫"
                description_text = "Te rugăm să descrii problema ta cât mai clar și detaliat."

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                user: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True,
                ),
                guild.me: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_channels=True,
                    manage_messages=True,
                    attach_files=True,
                    embed_links=True,
                ),
            }

            ping_roles = []
            for role_id in allowed_role_ids:
                if role_id is None:
                    continue

                role = guild.get_role(role_id)
                if role is None:
                    continue

                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True,
                )
                ping_roles.append(role.mention)

            if ticket_type == "password":
                category = guild.get_channel(settings.password_category_id)
            elif ticket_type == "unban":
                category = guild.get_channel(settings.unban_category_id)
            else:
                category = guild.get_channel(settings.general_category_id)

            if category is None or not isinstance(category, discord.CategoryChannel):
                await interaction.followup.send(
                    "Categoria pentru acest tip de ticket nu este configurată corect.",
                    ephemeral=True,
                )
                return

            channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
            )

            ticket = Ticket(
                guild_id=guild.id,
                channel_id=channel.id,
                creator_id=user.id,
                ticket_type=ticket_type,
                status="open",
            )
            session.add(ticket)
            await session.commit()

        embed = discord.Embed(
            title=f"{category_emoji} {category_label}",
            description=(
                f"Bun venit, {user.mention}.\n\n"
                f"{description_text}\n\n"
                "Un membru din echipă va răspunde cât mai curând."
            ),
            color=discord.Color.from_rgb(221, 255, 153),
        )
        embed.add_field(name="Creator", value=user.mention, inline=True)
        embed.add_field(name="Tip ticket", value=category_label, inline=True)
        embed.set_footer(text="Ratonii Tickets")

        mention_text = " ".join(dict.fromkeys(ping_roles))
        if mention_text:
            mention_text = f"{mention_text} {user.mention}"
        else:
            mention_text = user.mention

        await channel.send(
            content=mention_text,
            embed=embed,
            view=TicketView(),
        )

        await interaction.followup.send(
            f"Ticketul tău a fost creat: {channel.mention}",
            ephemeral=True,
        )

        if ticket_type == "password":
            await self.start_password_questions(channel, user)

    @discord.ui.button(
        label="Recuperare Parolă",
        style=discord.ButtonStyle.secondary,
        emoji="🔐",
        custom_id="ticket_open_password",
    )
    async def password_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await self.create_ticket(interaction, "password")

    @discord.ui.button(
        label="Ticket",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        custom_id="ticket_open_general",
    )
    async def general_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await self.create_ticket(interaction, "general")

    @discord.ui.button(
        label="Cerere Unban",
        style=discord.ButtonStyle.danger,
        emoji="🔨",
        custom_id="ticket_open_unban",
    )
    async def unban_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await self.create_ticket(interaction, "unban")