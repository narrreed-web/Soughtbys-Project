# run "pip install discord.py-self asyncio" for this to work

import discord
import asyncio
import random, os, sys, threading, time
from datetime import datetime

token = ""  # put ur shit here

msg = ""
sent = 0
failed = 0
blacklist = set()
running = True
targets = []
current = 0

class Bot(discord.Client):
    def __init__(self):
        super().__init__(self_bot=True, intents=discord.Intents.all())
        
    async def on_ready(self):
        global msg, targets
        
        print(f"logged in as {self.user}")
        await self.change_presence(status=discord.Status.idle, activity=discord.Game(name="with python"))
        
        # get the msg
        print("\n--- paste ur message, type STOP on new line when done ---\n")
        lines = []
        while True:
            try:
                line = input()
                if line.strip().upper() == "STOP":
                    break
                lines.append(line)
            except:
                break
        
        msg = "\n".join(lines)
        if not msg:
            print("no msg???")
            return
            
        print(f"\ngot it ({len(msg)} chars), scraping members...")
        
        # scrape everyone
        seen = set()
        for guild in self.guilds:
            try:
                print(f"scanning {guild.name}...")
                async for m in guild.fetch_members(limit=None):
                    if m.id == self.user.id or m.bot or m.id in seen:
                        continue
                    seen.add(m.id)
                    targets.append(m)
                await asyncio.sleep(random.uniform(1, 3))
            except Exception as e:
                print(f"rip {guild.name}: {e}")
                continue
        
        random.shuffle(targets)
        print(f"\nfound {len(targets)} ppl to dm")
        print("type STOP + enter anytime to quit")
        
        # load blacklist if exists
        if os.path.exists("blocked.txt"):
            with open("blocked.txt") as f:
                blacklist = set(int(x.strip()) for x in f if x.strip())
        
        # start stop listener
        t = threading.Thread(target=stop_check, daemon=True)
        t.start()
        
        await asyncio.sleep(3)
        await start_dming(self)
    
async def start_dming(client):
    global sent, failed, current, running
    
    start_time = time.time()
    
    while current < len(targets) and running:
        user = targets[current]
        current += 1
        
        if user.id in blacklist:
            continue
        
        # random delay - sometimes fast sometimes slow
        delay = random.uniform(4, 15)
        
        # 10% chance to take a piss break
        if random.random() < 0.1:
            delay = random.uniform(60, 180)
            print("* taking a quick break *")
        
        # slow down after hour
        if (time.time() - start_time) > 3600:
            delay += random.uniform(3, 8)
        
        await asyncio.sleep(delay)
        
        try:
            # open dm
            dm = user.dm_channel
            if not dm:
                dm = await user.create_dm()
                await asyncio.sleep(random.uniform(0.5, 2))
            
            # fake typing if msg long
            if len(msg) > 10:
                wpm = random.randint(50, 80)
                t = len(msg) / (wpm / 60) / 5  # rough calc
                async with dm.typing():
                    await asyncio.sleep(t)
            
            # send it
            await dm.send(msg)
            sent += 1
            
            # occasionally send followup (like u forgot something)
            if random.random() < 0.05:
                await asyncio.sleep(random.uniform(1, 3))
                await dm.send("lmk if u see this")
            
            if sent % 5 == 0:
                print(f"progress: {sent} sent, {failed} fucked")
            
            # change status sometimes
            if sent % 20 == 0:
                acts = [
                    discord.Game(name="Spotify"),
                    discord.Game(name="Visual Studio Code"),
                    discord.Activity(type=discord.ActivityType.watching, name="YouTube")
                ]
                await client.change_presence(status=random.choice([discord.Status.online, discord.Status.idle]), 
                                           activity=random.choice(acts))
            
            # big break every 40-60 msgs
            if sent % random.randint(40, 60) == 0:
                mins = random.randint(3, 5)
                print(f"chilling for {mins} mins...")
                await asyncio.sleep(mins * 60)
                
        except discord.Forbidden:
            # blocked or dms closed
            blacklist.add(user.id)
            with open("blocked.txt", "a") as f:
                f.write(f"{user.id}\n")
            failed += 1
            
        except discord.HTTPException as e:
            if e.status == 429:
                print(f"rate limited, sleeping {e.retry_after}s")
                await asyncio.sleep(e.retry_after + random.randint(5, 15))
            else:
                failed += 1
                
        except Exception as e:
            print(f"error: {e}")
            failed += 1
    
    print(f"\ndone. sent {sent}, failed {failed}")
    input("press enter to die")

def stop_check():
    global running
    while running:
        try:
            x = input().strip().upper()
            if x == "STOP":
                print("stopping after this one...")
                running = False
                break
        except:
            time.sleep(0.5)

if __name__ == "__main__":
    tok = token if token else input("token: ").strip()
    if not tok:
        print("no token dumbass")
        sys.exit()
    
    b = Bot()
    try:
        b.run(tok)
    except Exception as e:
        print(f"ded: {e}")
