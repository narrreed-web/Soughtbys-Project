"""
-------------------------------------------
Drop a trap channel in your server. Anyone who sends a message there gets
hit with whatever punishment you've configured (ban / softban / kick), and
a per-guild counter is updated.

Commands (prefix "!"):
    !config channel #channel        Set the honeypot channel
    !config action ban|softban|kick Set what happens when it's triggered
    !config log #channel            (optional) where to log catches
    !config show                    Show current config + counters
    !panel                          Post the warning panel (Components V2)

Setup: see the .env instructions at the bottom of this file, or the
README. You need a `.env` file next to this script containing:

    DISCORD_BOT_TOKEN=your-token-here

Requires: discord.py>=2.6, python-dotenv
    pip install discord.py python-dotenv

Required bot permissions: Ban Members, Kick Members, Manage Messages,
View Channels, Send Messages. Required privileged intent: Message
Content Intent (enable it in the Discord Developer Portal, Bot tab).
"""

import os
import json
import logging
import threading

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()  # reads .env in the current working directory

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("honeypot")

COMMAND_PREFIX = "!"
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

VALID_ACTIONS = {"ban", "softban", "kick"}

# ---------------------------------------------------------------------
# Storage (simple JSON file, kept in this same script for simplicity)
# ---------------------------------------------------------------------

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
_lock = threading.Lock()

DEFAULT_GUILD_CONFIG = {
    "honeypot_channel_id": None,
    "action": "ban",
    "log_channel_id": None,
    "counters": {"ban": 0, "softban": 0, "kick": 0},
}


def _load() -> dict:
    if not os.path.exists(DATA_PATH):
        return {}
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def _save(data: dict) -> None:
    tmp_path = DATA_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, DATA_PATH)


def get_guild_config(guild_id: int) -> dict:
    with _lock:
        data = _load()
        gid = str(guild_id)
        if gid not in data:
            data[gid] = json.loads(json.dumps(DEFAULT_GUILD_CONFIG))
            _save(data)
        return data[gid]


def update_guild_config(guild_id: int, **kwargs) -> dict:
    with _lock:
        data = _load()
        gid = str(guild_id)
        if gid not in data:
            data[gid] = json.loads(json.dumps(DEFAULT_GUILD_CONFIG))
        data[gid].update(kwargs)
        _save(data)
        return data[gid]


def increment_counter(guild_id: int, action: str) -> dict:
    with _lock:
        data = _load()
        gid = str(guild_id)
        if gid not in data:
            data[gid] = json.loads(json.dumps(DEFAULT_GUILD_CONFIG))
        counters = data[gid].setdefault("counters", {"ban": 0, "softban": 0, "kick": 0})
        counters[action] = counters.get(action, 0) + 1
        _save(data)
        return data[gid]


# ---------------------------------------------------------------------
# Bot setup
# ---------------------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)

HAS_COMPONENTS_V2 = hasattr(discord.ui, "LayoutView")


def has_manage_guild():
    async def predicate(ctx: commands.Context):
        if ctx.author.guild_permissions.manage_guild:
            return True
        await ctx.reply("You need the **Manage Server** permission to use this.")
        return False
    return commands.check(predicate)


# ---------------------------------------------------------------------
# !config command group
# ---------------------------------------------------------------------

@bot.group(name="config", invoke_without_command=True)
@has_manage_guild()
async def config_group(ctx: commands.Context):
    await show_config(ctx)


@config_group.command(name="channel")
@has_manage_guild()
async def config_channel(ctx: commands.Context, channel: discord.TextChannel):
    update_guild_config(ctx.guild.id, honeypot_channel_id=channel.id)
    await ctx.reply(f"Honeypot channel set to {channel.mention}.")


@config_group.command(name="action")
@has_manage_guild()
async def config_action(ctx: commands.Context, action: str):
    action = action.lower()
    if action not in VALID_ACTIONS:
        await ctx.reply(f"Action must be one of: {', '.join(sorted(VALID_ACTIONS))}")
        return
    update_guild_config(ctx.guild.id, action=action)
    await ctx.reply(f"Honeypot action set to **{action}**.")


@config_group.command(name="log")
@has_manage_guild()
async def config_log(ctx: commands.Context, channel: discord.TextChannel):
    update_guild_config(ctx.guild.id, log_channel_id=channel.id)
    await ctx.reply(f"Log channel set to {channel.mention}.")


@config_group.command(name="show")
@has_manage_guild()
async def config_show(ctx: commands.Context):
    await show_config(ctx)


async def show_config(ctx: commands.Context):
    cfg = get_guild_config(ctx.guild.id)
    channel = ctx.guild.get_channel(cfg["honeypot_channel_id"]) if cfg["honeypot_channel_id"] else None
    log_channel = ctx.guild.get_channel(cfg["log_channel_id"]) if cfg["log_channel_id"] else None
    counters = cfg["counters"]

    embed = discord.Embed(title="Honeypot Configuration", color=discord.Color.red())
    embed.add_field(name="Honeypot channel", value=channel.mention if channel else "Not set", inline=False)
    embed.add_field(name="Action", value=f"`{cfg['action']}`", inline=False)
    embed.add_field(name="Log channel", value=log_channel.mention if log_channel else "Not set", inline=False)
    embed.add_field(
        name="Counters",
        value=f"Bans: **{counters.get('ban', 0)}**\n"
              f"Softbans: **{counters.get('softban', 0)}**\n"
              f"Kicks: **{counters.get('kick', 0)}**",
        inline=False,
    )
    await ctx.reply(embed=embed)


# ---------------------------------------------------------------------
# Honeypot trigger
# ---------------------------------------------------------------------

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or message.guild is None:
        return

    cfg = get_guild_config(message.guild.id)
    honeypot_id = cfg.get("honeypot_channel_id")

    if honeypot_id and message.channel.id == honeypot_id:
        await handle_catch(message, cfg)
        return

    await bot.process_commands(message)


async def handle_catch(message: discord.Message, cfg: dict):
    guild = message.guild
    member = message.author
    action = cfg.get("action", "ban")
    reason = "Honeypot trigger: sent a message in the trap channel."

    try:
        await message.delete()
    except discord.HTTPException:
        pass

    success = False
    try:
        if action == "ban":
            await guild.ban(member, reason=reason, delete_message_days=1)
            success = True
        elif action == "kick":
            await guild.kick(member, reason=reason)
            success = True
        elif action == "softban":
            await guild.ban(member, reason=reason, delete_message_days=1)
            await guild.unban(member, reason="Softban cleanup")
            success = True
    except discord.Forbidden:
        log.warning("Missing permissions to %s %s in %s", action, member, guild.name)
    except discord.HTTPException as e:
        log.warning("Failed to %s %s: %s", action, member, e)

    if success:
        increment_counter(guild.id, action)

    log_channel_id = cfg.get("log_channel_id")
    if log_channel_id:
        log_channel = guild.get_channel(log_channel_id)
        if log_channel:
            status = "✅" if success else "⚠️ failed"
            try:
                await log_channel.send(
                    f"{status} Honeypot triggered by {member.mention} (`{member.id}`) — action: `{action}`"
                )
            except discord.HTTPException:
                pass


# ---------------------------------------------------------------------
# !panel — Components V2 honeypot warning message
# ---------------------------------------------------------------------

if HAS_COMPONENTS_V2:

    class HoneypotPanel(discord.ui.LayoutView):
        def __init__(self, counters: dict):
            super().__init__(timeout=None)
            container = discord.ui.Container(accent_color=discord.Color.red())
            container.add_item(
                discord.ui.TextDisplay("## DO NOT SEND MESSAGES IN THIS CHANNEL")
            )
            container.add_item(
                discord.ui.TextDisplay(
                    "This channel is used to catch compromised users (idiots). "
                    "Any messages sent here will result in a **punishment**."
                )
            )
            container.add_item(discord.ui.Separator())
            container.add_item(
                discord.ui.TextDisplay(
                    f"Bans: **{counters.get('ban', 0)}**  |  "
                    f"Softbans: **{counters.get('softban', 0)}**  |  "
                    f"Kicks: **{counters.get('kick', 0)}**"
                )
            )
            self.add_item(container)


@bot.command(name="panel")
@has_manage_guild()
async def panel(ctx: commands.Context):
    cfg = get_guild_config(ctx.guild.id)
    counters = cfg["counters"]

    if HAS_COMPONENTS_V2:
        view = HoneypotPanel(counters)
        await ctx.send(view=view)
    else:
        embed = discord.Embed(
            title="DO NOT SEND MESSAGES IN THIS CHANNEL",
            description=(
                "This channel is used to catch compromised users (idiots). "
                "Any messages sent here will result in a **punishment**.\n\n"
                f"Bans: **{counters.get('ban', 0)}**  |  "
                f"Softbans: **{counters.get('softban', 0)}**  |  "
                f"Kicks: **{counters.get('kick', 0)}**"
            ),
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)

    try:
        await ctx.message.delete()
    except discord.HTTPException:
        pass


@bot.event
async def on_ready():
    log.info("Logged in as %s (id: %s)", bot.user, bot.user.id)
    log.info("Components V2 support: %s", HAS_COMPONENTS_V2)


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit(
            "DISCORD_BOT_TOKEN not found.\n"
            "Create a .env file next to this script containing:\n"
            "    DISCORD_BOT_TOKEN=your-token-here\n"
            "See the setup instructions in README.md / .env.example."
        )
    bot.run(TOKEN)
