from __future__ import annotations

import html
import io
from datetime import datetime, timezone

import discord


async def build_transcript_file(channel: discord.TextChannel) -> discord.File:
    messages = []
    async for message in channel.history(limit=None, oldest_first=True):
        created_at = message.created_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        author_name = html.escape(str(message.author))
        content = html.escape(message.content or "")

        attachments_html = ""
        if message.attachments:
            links = []
            for attachment in message.attachments:
                safe_name = html.escape(attachment.filename)
                safe_url = html.escape(attachment.url)
                links.append(f'<li><a href="{safe_url}" target="_blank">{safe_name}</a></li>')
            attachments_html = f"""
                <div class="attachments">
                    <strong>Atașamente:</strong>
                    <ul>
                        {''.join(links)}
                    </ul>
                </div>
            """

        embeds_html = ""
        if message.embeds:
            embeds_html = '<div class="embed-note">[Mesajul conține embed-uri]</div>'

        messages.append(
            f"""
            <div class="message">
                <div class="meta">
                    <span class="author">{author_name}</span>
                    <span class="time">{created_at}</span>
                </div>
                <div class="content">{content if content else "<i>[Fără text]</i>"}</div>
                {attachments_html}
                {embeds_html}
            </div>
            """
        )

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    channel_name = html.escape(channel.name)
    guild_name = html.escape(channel.guild.name)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ro">
    <head>
        <meta charset="UTF-8">
        <title>Transcript - {channel_name}</title>
        <style>
            body {{
                background: #0f1115;
                color: #e6e6e6;
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 24px;
            }}
            .container {{
                max-width: 1000px;
                margin: 0 auto;
            }}
            .header {{
                background: #161a22;
                border: 1px solid #2b3240;
                border-radius: 14px;
                padding: 18px 20px;
                margin-bottom: 18px;
            }}
            .header h1 {{
                margin: 0 0 8px 0;
                font-size: 24px;
            }}
            .header p {{
                margin: 4px 0;
                color: #b8c0cc;
            }}
            .message {{
                background: #161a22;
                border: 1px solid #2b3240;
                border-radius: 14px;
                padding: 14px 16px;
                margin-bottom: 12px;
            }}
            .meta {{
                margin-bottom: 8px;
            }}
            .author {{
                font-weight: 700;
                color: #d7f78d;
                margin-right: 10px;
            }}
            .time {{
                color: #9aa4b2;
                font-size: 13px;
            }}
            .content {{
                white-space: pre-wrap;
                word-break: break-word;
                line-height: 1.5;
            }}
            .attachments {{
                margin-top: 10px;
            }}
            .attachments ul {{
                margin: 6px 0 0 18px;
            }}
            a {{
                color: #7cc7ff;
            }}
            .embed-note {{
                margin-top: 8px;
                color: #c9a227;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Transcript Ticket</h1>
                <p><strong>Server:</strong> {guild_name}</p>
                <p><strong>Canal:</strong> {channel_name}</p>
                <p><strong>Generat la:</strong> {generated_at}</p>
            </div>
            {''.join(messages) if messages else '<div class="message"><i>Nu există mesaje în acest ticket.</i></div>'}
        </div>
    </body>
    </html>
    """

    transcript_bytes = io.BytesIO(html_content.encode("utf-8"))
    filename = f"transcript-{channel.name}.html"
    return discord.File(transcript_bytes, filename=filename)