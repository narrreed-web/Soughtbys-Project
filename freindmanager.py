# run pip install discord.py-self asyncio tinker for this to work
import discord
import asyncio
import tkinter as tk
from tkinter import messagebox, scrolledtext
import threading
import time
import random

# put ur token here or leave empty n paste in gui
token = ""

class Manager:
    def __init__(self):
        self.client = discord.Client(intents=discord.Intents.all())
        self.running = False
        self.min_delay = 5
        self.max_delay = 15
        
    async def wait(self):
        # random delay between actions
        d = random.uniform(self.min_delay, self.max_delay)
        # 5% chance to take longer break
        if random.random() < 0.05:
            d += random.uniform(20, 60)
        await asyncio.sleep(d)

    async def block_all(self, log_func):
        # get friends
        friends = []
        for u in self.client.users:
            if isinstance(u, discord.User) and u != self.client.user:
                friends.append(u)
        
        log_func(f"found {len(friends)} friends")
        
        for i, user in enumerate(friends):
            if not self.running:
                log_func("stopped")
                return
            
            try:
                # pretend to read profile
                await asyncio.sleep(random.uniform(0.5, 2))
                await user.block()
                log_func(f"blocked {user.name} ({i+1}/{len(friends)})")
                await self.wait()
            except Exception as e:
                log_func(f"blocked {user.name}: {e}")

    async def unblock_all(self, log_func):
        # get blocked ppl
        blocked = []
        try:
            # discord stores this weirdly
            for rel in self.client.relationships:
                if rel.type == discord.RelationshipType.blocked:
                    blocked.append(rel.user)
        except:
            log_func("couldnt get blocked list")
            return
        
        log_func(f"unblocking {len(blocked)} users")
        
        for i, user in enumerate(blocked):
            if not self.running:
                return
            try:
                await user.unblock()
                log_func(f"unblocked {user.name}")
                await self.wait()
            except Exception as e:
                log_func(f"failed: {e}")

    async def unfriend_all(self, log_func):
        # find all friends
        friends = []
        for rel in self.client.relationships:
            if rel.type == discord.RelationshipType.friend:
                friends.append(rel.user)
        
        log_func(f"removing {len(friends)} friends (this takes ages)")
        
        for i, user in enumerate(friends):
            if not self.running:
                return
            try:
                # unfriending is sus so go slower
                await asyncio.sleep(random.uniform(8, 20))
                await user.remove_friend()
                log_func(f"unfriended {user.name} ({i+1}/{len(friends)})")
                await self.wait()
            except Exception as e:
                log_func(f"error: {e}")

    async def close_dms(self, log_func):
        dms = []
        for ch in self.client.private_channels:
            if isinstance(ch, discord.DMChannel):
                dms.append(ch)
        
        log_func(f"closing {len(dms)} dms")
        
        for i, dm in enumerate(dms):
            if not self.running:
                return
            try:
                name = dm.recipient.name if dm.recipient else "unknown"
                await dm.delete()
                log_func(f"closed dm with {name}")
                await asyncio.sleep(random.uniform(2, 5))
            except Exception as e:
                log_func(f"failed: {e}")

    async def cancel_requests(self, log_func):
        pending = []
        for rel in self.client.relationships:
            if rel.type == discord.RelationshipType.outgoing_request:
                pending.append(rel)
        
        log_func(f"cancelling {len(pending)} requests")
        
        for rel in pending:
            if not self.running:
                return
            try:
                await rel.user.remove_friend()
                log_func(f"cancelled to {rel.user.name}")
                await self.wait()
            except Exception as e:
                log_func(f"error: {e}")

# gui setup
class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("discord friend nuker")
        self.root.geometry("600x500")
        self.root.configure(bg='#222')
        
        self.mgr = Manager()
        self.bot_thread = None
        
        # token input
        tk.Label(self.root, text="Token:", bg='#222', fg='white').pack(pady=5)
        self.token_box = tk.Entry(self.root, width=50, show="*")
        self.token_box.pack()
        self.token_box.insert(0, token)
        
        tk.Button(self.root, text="Connect", command=self.connect, 
                 bg='#444', fg='white').pack(pady=5)
        
        # status
        self.status = tk.Label(self.root, text="disconnected", fg='red', bg='#222')
        self.status.pack()
        
        # delay config
        frame = tk.Frame(self.root, bg='#222')
        frame.pack(pady=10)
        
        tk.Label(frame, text="Min delay:", bg='#222', fg='white').pack(side='left')
        self.min_spin = tk.Spinbox(frame, from_=1, to=60, width=5)
        self.min_spin.pack(side='left')
        self.min_spin.delete(0,'end')
        self.min_spin.insert(0,'8')
        
        tk.Label(frame, text="Max:", bg='#222', fg='white').pack(side='left', padx=(10,0))
        self.max_spin = tk.Spinbox(frame, from_=5, to=300, width=5)
        self.max_spin.pack(side='left')
        self.max_spin.delete(0,'end')
        self.max_spin.insert(0,'20')
        
        # buttons
        btn_frame = tk.Frame(self.root, bg='#222')
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Block All", command=lambda: self.run('block'),
                 bg='#d63031', fg='white', width=12).grid(row=0, column=0, padx=5, pady=5)
        tk.Button(btn_frame, text="Unblock All", command=lambda: self.run('unblock'),
                 bg='#00b894', fg='white', width=12).grid(row=0, column=1, padx=5, pady=5)
        tk.Button(btn_frame, text="Unfriend All", command=lambda: self.run('unfriend'),
                 bg='#e17055', fg='white', width=12).grid(row=0, column=2, padx=5, pady=5)
        tk.Button(btn_frame, text="Close DMs", command=lambda: self.run('close'),
                 bg='#0984e3', fg='white', width=12).grid(row=1, column=0, padx=5, pady=5)
        tk.Button(btn_frame, text="Cancel Req", command=lambda: self.run('cancel'),
                 bg='#fdcb6e', fg='black', width=12).grid(row=1, column=1, padx=5, pady=5)
        
        # stop button
        tk.Button(self.root, text="STOP", command=self.stop, bg='#ff0000', 
                 fg='white', font=('bold'), width=20).pack(pady=5)
        
        # log box
        tk.Label(self.root, text="Logs:", bg='#222', fg='white').pack()
        self.logs = scrolledtext.ScrolledText(self.root, height=12, bg='#111', fg='#0f0')
        self.logs.pack(fill='both', expand=True, padx=10, pady=5)
        
    def log(self, msg):
        t = time.strftime('%H:%M:%S')
        self.logs.insert('end', f'[{t}] {msg}\n')
        self.logs.see('end')
        
    def connect(self):
        t = self.token_box.get().strip()
        if not t:
            messagebox.showerror("error", "enter token dumbfuck")
            return
            
        self.log("connecting...")
        self.status.config(text="connecting...", fg='orange')
        
        def run_bot():
            @self.mgr.client.event
            async def on_ready():
                self.status.config(text=f"online as {self.mgr.client.user}", fg='green')
                self.log(f"connected as {self.mgr.client.user}")
            
            try:
                self.mgr.client.run(t)
            except Exception as e:
                self.log(f"error: {e}")
                self.status.config(text="failed", fg='red')
        
        self.bot_thread = threading.Thread(target=run_bot, daemon=True)
        self.bot_thread.start()
        
    def run(self, action):
        if not self.mgr.client.is_ready():
            messagebox.showerror("error", "not connected yet")
            return
            
        # update delays from spinboxes
        try:
            self.mgr.min_delay = float(self.min_spin.get())
            self.mgr.max_delay = float(self.max_spin.get())
        except:
            pass
            
        self.mgr.running = True
        self.log(f"starting {action}...")
        
        async def do_it():
            if action == 'block':
                await self.mgr.block_all(self.log)
            elif action == 'unblock':
                await self.mgr.unblock_all(self.log)
            elif action == 'unfriend':
                await self.mgr.unfriend_all(self.log)
            elif action == 'close':
                await self.mgr.close_dms(self.log)
            elif action == 'cancel':
                await self.mgr.cancel_requests(self.log)
            self.log("done")
        
        # run in async thread
        def thread():
            asyncio.run_coroutine_threadsafe(do_it(), self.mgr.client.loop)
        
        threading.Thread(target=thread, daemon=True).start()
        
    def stop(self):
        self.mgr.running = False
        self.log("stopping...")

if __name__ == "__main__":
    app = App()
    app.root.mainloop()
