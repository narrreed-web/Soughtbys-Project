# commands, safest to least safe.
# [SAFE] - low detection
# .ping - check latency
# .stats - view counters
# .autoreact <emoji> - auto react to msgs (40% chance so not as dtc)
# .setreply - set auto reply text
# .stopdm - stop mass dm
# [MEDIUM] - moderate risk
# .togglenitro - nitro sniper (has delays but still fast)
# .toggleautoreply - auto replies to DMs (instant replies look botty)
# [HIGH RISK] - likely ban
# .dmadvertise - mass DMs everyone in all servers (major ToS violation, easy to detect/report)


# RUN pip install discord.py-self asyncio in your console for this to work


import discord
from discord.ext import commands
import asyncio
import random
import os
import sys
import threading
import time
from datetime import datetime

TOKEN = ""
PREFIX = "."
OWNER_ID = 0  # ur discord id here

# feature toggles
nitro_on = True
auto_reply_on = False
auto_react = None  # emoji string or None
dm_ad_running = False

# globals for tracking
replies_sent = 0
nitros_claimed = 0
dm_sent = 0
blacklist = set()
custom_reply_msg = "im busy rn ill reply later"  # default auto reply

# regex for nitro
nitro_re = re.compile(r'(?:discord\.(?:gift|gifts))\/([a-zA-Z0-9-]{16,24})')

bot = commands.Bot(command_prefix=PREFIX, self_bot=True, intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f"[+] Selfbot online as {bot.user}")
    print(f"[+] Prefix: {PREFIX}")
    print(f"[+] Nitro sniper: {'ON' if nitro_on else 'OFF'}")
    print(f"[+] Auto reply: {'ON' if auto_reply_on else 'OFF'}")
    await bot.change_presence(status=discord.Status.online, activity=discord.Game(name="with code"))

@bot.event
async def on_message(msg):
    global nitros_claimed, replies_sent
    
    # ignore self
    if msg.author.id == bot.user.id:
        return
    
    # === NITRO SNIPER [MEDIUM RISK - fast claims detectable] ===
    if nitro_on:
        text = msg.content or ""
        for emb in msg.embeds:
            if emb.url: text += emb.url
        
        codes = nitro_re.findall(text)
        if codes:
            for code in codes:
                if len(code) < 16: continue
                
                # delay to not be instant
                await asyncio.sleep(random.uniform(0.3, 1.2))
                
                url = f"https://discord.com/api/v10/entitlements/gift-codes/{code}/redeem"
                headers = {
                    "Authorization": TOKEN,
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
                }
                body = {"channel_id": str(msg.channel.id)}
                
                try:
                    import aiohttp
                    async with aiohttp.ClientSession() as s:
                        r = await s.put(url, json=body, headers=headers)
                        if r.status == 200:
                            print(f"[+] SNIPED: {code}")
                            nitros_claimed += 1
                        elif r.status == 400:
                            j = await r.json()
                            if "redeemed" in j.get("message", "").lower():
                                print(f"[-] Late: {code}")
                except Exception as e:
                    pass
    
    # === AUTO REPLY [HIGH RISK - instant replies look botty] ===
    if auto_reply_on and isinstance(msg.channel, discord.DMChannel):
        # only reply to DMs not servers (safer)
        if msg.author.id != OWNER_ID:  # dont auto reply to urself
            await asyncio.sleep(random.uniform(2, 5))  # fake typing delay
            await msg.channel.send(custom_reply_msg)
            replies_sent += 1
            print(f"[*] Auto replied to {msg.author}")
    
    # === AUTO REACT [SAFE - low risk if not spammy] ===
    if auto_react and random.random() < 0.4:  # 40% chance only
        try:
            await msg.add_reaction(auto_react)
        except:
            pass
    
    await bot.process_commands(msg)

# === COMMANDS ===

@bot.command()
async def ping(ctx):
    """[SAFE] check if bot alive"""
    await ctx.send(f"latency: {round(bot.latency*1000)}ms", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def togglenitro(ctx):
    """[SAFE] toggle nitro sniper on/off"""
    global nitro_on
    nitro_on = not nitro_on
    await ctx.send(f"nitro sniper: {'ON' if nitro_on else 'OFF'}", delete_after=3)
    await ctx.message.delete()

@bot.command()
async def toggleautoreply(ctx):
    """[MEDIUM] toggle auto reply"""
    global auto_reply_on
    auto_reply_on = not auto_reply_on
    await ctx.send(f"auto reply: {'ON' if auto_reply_on else 'OFF'}", delete_after=3)
    await ctx.message.delete()

@bot.command()
async def setreply(ctx, *, text):
    """[SAFE] set auto reply message"""
    global custom_reply_msg
    custom_reply_msg = text
    await ctx.send("auto reply msg set", delete_after=3)
    await ctx.message.delete()

@bot.command()
async def toggleauto(ctx):
    """[SAFE] toggle auto reactions"""
    await ctx.send("use .autoreact <emoji> to set, or .stopreact to disable", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def autoreact(ctx, emoji):
    """[SAFE] set auto react emoji"""
    global auto_react
    auto_react = emoji
    await ctx.send(f"will react with {emoji}", delete_after=3)
    await ctx.message.delete()

@bot.command()
async def stopreact(ctx):
    """[SAFE] stop auto reacting"""
    global auto_react
    auto_react = None
    await ctx.send("auto react off", delete_after=3)
    await ctx.message.delete()

@bot.command()
async def stats(ctx):
    """[SAFE] show stats"""
    embed = discord.Embed(title="Selfbot Stats", color=0x00ff00)
    embed.add_field(name="Nitros Claimed", value=str(nitros_claimed))
    embed.add_field(name="Auto Replies", value=str(replies_sent))
    embed.add_field(name="DMs Sent", value=str(dm_sent))
    await ctx.send(embed=embed, delete_after=10)
    await ctx.message.delete()

# === DM ADVERTISER [HIGH RISK - mass DM is major ToS violation] ===

@bot.command()
async def dmadvertise(ctx):
    """[HIGH RISK] mass DM everyone in servers"""
    global dm_ad_running, dm_sent
    
    if dm_ad_running:
        await ctx.send("already running bro", delete_after=3)
        return
    
    # get message
    await ctx.send("check ur console for input...", delete_after=3)
    
    print("\n" + "="*50)
    print("DM ADVERTISER - HIGH DETECTION RISK")
    print("="*50)
    print("enter message (STOP on new line to finish):")
    
    lines = []
    while True:
        try:
            line = input("> ")
            if line.strip().upper() == "STOP":
                break
            lines.append(line)
        except:
            break
    
    ad_msg = "\n".join(lines)
    if not ad_msg:
        print("no msg, canceling")
        return
    
    print(f"loaded: {len(ad_msg)} chars")
    print("starting in 5s... (Ctrl+C to abort)")
    await asyncio.sleep(5)
    
    dm_ad_running = True
    
    # scrape targets
    targets = []
    seen = set()
    
    for guild in bot.guilds:
        try:
            print(f"scanning {guild.name}...")
            async for m in guild.fetch_members(limit=None):
                if m.id == bot.user.id or m.bot or m.id in seen or m.id in blacklist:
                    continue
                seen.add(m.id)
                targets.append(m)
            await asyncio.sleep(1)
        except Exception as e:
            print(f"rip {guild.name}: {e}")
            continue
    
    random.shuffle(targets)
    print(f"\n{len(targets)} targets, sending...")
    
    for user in targets:
        if not dm_ad_running:
            break
        
        try:
            # open dm
            dm = user.dm_channel
            if not dm:
                dm = await user.create_dm()
                await asyncio.sleep(random.uniform(1, 3))
            
            # typing sim for long msgs
            if len(ad_msg) > 20:
                async with dm.typing():
                    await asyncio.sleep(random.uniform(2, 5))
            
            await dm.send(ad_msg)
            dm_sent += 1
            print(f"[+] {user}")
            
            # random delay 5-20s
            await asyncio.sleep(random.uniform(5, 20))
            
        except discord.Forbidden:
            blacklist.add(user.id)
            with open("blocked.txt", "a") as f:
                f.write(f"{user.id}\n")
            print(f"[-] blocked/closed: {user}")
        except Exception as e:
            print(f"[!] error: {e}")
    
    dm_ad_running = False
    print(f"\ndone. sent {dm_sent}")

@bot.command()
async def stopdm(ctx):
    """[SAFE] stop dm advertiser"""
    global dm_ad_running
    dm_ad_running = False
    await ctx.send("stopping dm ad...", delete_after=3)

if __name__ == "__main__":
    tok = TOKEN if TOKEN else input("token: ").strip()
    if not tok:
        print("no token")
        sys.exit()
    
    print("="*50)
    print("SELFBOT LOADED")
    print("Commands:")
    print(f"{PREFIX}ping - check latency [SAFE]")
    print(f"{PREFIX}togglenitro - nitro sniper on/off [MEDIUM]")
    print(f"{PREFIX}toggleautoreply - auto reply [HIGH]")
    print(f"{PREFIX}dmadvertise - mass DM [HIGH RISK]")
    print(f"{PREFIX}autoreact <emoji> - auto react [SAFE]")
    print("="*50)
    
    bot.run(tok)
