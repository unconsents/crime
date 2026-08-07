import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from bootstrap import ensure_packages
ensure_packages()

import asyncio
import json

from core import (
    load_config, load_presence, save_presence, make_embed,
    FluxerREST, cprint, print_banner, COOLDOWNS_DEF,
    AUTO_DELETE_SECONDS, AFK_REPLY_MIN_INTERVAL_SECONDS,
    GATEWAY_WS_URL, fetch_credit_line, print_credit_line,
)

import time
import websockets

from stats import bump_event, bump_request, title_update_loop, uptime_str as stats_uptime_str

from cogs.fun import FunCog
from cogs.utils import UtilsCog
from cogs.moderation import ModerationCog
from cogs.presence import PresenceCog
from cogs.misc import MiscCog

class CrimeBot:
    def __init__(self):
        self.config = load_config()
        self.presence = load_presence()
        self.rest = FluxerREST(self.config["token"])
        self.rest.on_request = bump_request
        self.ws = None
        self.state = {
            "user_id": None,
            "username": None,
            "session_id": None,
            "sequence": None,
            "afk_active": False,
            "afk_reason": "AFK",
            "last_afk_reply_time": 0.0,
        }
        self.cooldowns = {}
        self.cogs = {
            "fun":        FunCog(self),
            "utils":      UtilsCog(self),
            "moderation": ModerationCog(self),
            "presence":   PresenceCog(self),
            "misc":       MiscCog(self),
        }

    def on_cooldown(self, cmd):
        if cmd not in COOLDOWNS_DEF:
            return False, 0
        remaining = COOLDOWNS_DEF[cmd] - (time.monotonic() - self.cooldowns.get(cmd, 0))
        return remaining > 0, max(0.0, remaining)

    def set_cooldown(self, cmd):
        self.cooldowns[cmd] = time.monotonic()

    async def auto_delete(self, channel_id, message_id, delay=AUTO_DELETE_SECONDS):
        await asyncio.sleep(delay)
        await self.rest.delete(channel_id, message_id)

    async def say(self, channel_id, embed, fallback=None):
        msg = await self.rest.send(channel_id, embeds=embed)
        if not msg and fallback:
            msg = await self.rest.send(channel_id, content=fallback)
        if msg:
            asyncio.create_task(self.auto_delete(channel_id, msg["id"]))
        return msg

    async def say_text(self, channel_id, text):
        msg = await self.rest.send(channel_id, content=text)
        if msg:
            asyncio.create_task(self.auto_delete(channel_id, msg["id"]))
        return msg

    async def sad(self, channel_id, description):
        await self.say(channel_id, make_embed("❌ Error", description), fallback=f"X {description}")

    async def send_presence_update(self, status=None, custom_status_text="__unset__"):
        if self.ws is None:
            cprint("[crime] cannot update presence: not connected to gateway yet.")
            return False
        d = {"since": None, "afk": False}
        if status is not None:
            d["status"] = status
        if custom_status_text != "__unset__":
            d["custom_status"] = {"text": custom_status_text} if custom_status_text else None
        try:
            await self.ws.send(json.dumps({"op": 3, "d": d}))
            return True
        except Exception as e:
            cprint(f"[crime] failed to send presence update: {type(e).__name__}: {e}")
            return False

    async def handle_command(self, cmd, args, channel_id, message_id, guild_id, author):
        if author.get("id") != self.state["user_id"]:
            return

        in_cd, remaining = self.on_cooldown(cmd)
        if in_cd:
            await self.say(channel_id, make_embed("Cooldown", f"`{self.config['prefix']}{cmd}` is on cooldown for **{remaining:.1f}s**.", color=0x111111))
            return

        self.set_cooldown(cmd)
        arg = " ".join(args)

        try:
            for cog in self.cogs.values():
                if cog.__class__.__name__ == "FunCog":
                    result = await cog.handle(cmd, args, arg, channel_id, self.config)
                elif cog.__class__.__name__ == "UtilsCog":
                    result = await cog.handle(cmd, args, arg, channel_id, guild_id, self.config)
                elif cog.__class__.__name__ == "ModerationCog":
                    result = await cog.handle(cmd, args, arg, channel_id, guild_id, self.config)
                elif cog.__class__.__name__ == "PresenceCog":
                    result = await cog.handle(cmd, args, arg, channel_id, self.config)
                elif cog.__class__.__name__ == "MiscCog":
                    result = await cog.handle(cmd, args, arg, channel_id, self.config)
                else:
                    result = False
                if result:
                    return

            await self.say(channel_id, make_embed("Unknown Command", f"Use `{self.config['prefix']}help` to see available commands."))

        except Exception as e:
            cprint(f"[crime] command error [{cmd}]: {type(e).__name__}: {e}")
            await self.say(channel_id, make_embed("❌ Error", f"Something went wrong running `{self.config['prefix']}{cmd}`.\n`{type(e).__name__}: {e}`", color=0x111111))

    async def handle_message(self, data):
        author     = data.get("author", {})
        is_self    = author.get("id") == self.state["user_id"]
        content    = data.get("content", "")
        channel_id = data["channel_id"]
        message_id = data["id"]
        guild_id   = data.get("guild_id")
        mentions   = data.get("mentions", [])
        prefix     = self.config["prefix"]

        if not is_self and content.startswith(prefix):
            return

        if is_self and content.startswith(prefix):
            await self.rest.delete(channel_id, message_id)
            parts = content[len(prefix):].split()
            if parts:
                await self.handle_command(parts[0].lower(), parts[1:], channel_id, message_id, guild_id, author)
            return

        if not is_self and self.state["afk_active"] and mentions:
            if any(u.get("id") == self.state["user_id"] for u in mentions):
                now = time.monotonic()
                if now - self.state["last_afk_reply_time"] >= AFK_REPLY_MIN_INTERVAL_SECONDS:
                    self.state["last_afk_reply_time"] = now
                    await self.say(channel_id, make_embed("AFK", f"**{self.state['username']}** is currently AFK: {self.state['afk_reason']}"))

    async def heartbeat_loop(self, ws, interval_ms):
        interval = interval_ms / 1000
        while True:
            await asyncio.sleep(interval)
            await ws.send(json.dumps({"op": 1, "d": self.state["sequence"]}))

    async def run_gateway(self):
        ws_url = f"{GATEWAY_WS_URL}?v=1&encoding=json"
        async with websockets.connect(ws_url) as ws:
            self.ws = ws
            hello = json.loads(await ws.recv())
            interval_ms = hello["d"]["heartbeat_interval"]
            heartbeat_task = asyncio.create_task(self.heartbeat_loop(ws, interval_ms))
            identify_data = {
                "token": self.config["token"],
                "properties": {"os": "windows", "browser": "crime", "device": "crime"},
                "intents": 0,
            }
            explicit_status = self.cogs["presence"].effective_status(self.presence)
            presence_block = {"afk": False}
            if explicit_status:
                presence_block["status"] = explicit_status
            if self.presence.get("custom_status"):
                presence_block["custom_status"] = {"text": self.presence["custom_status"]}
            if len(presence_block) > 1:
                identify_data["presence"] = presence_block
            await ws.send(json.dumps({"op": 2, "d": identify_data}))
            try:
                async for raw in ws:
                    payload    = json.loads(raw)
                    op         = payload.get("op")
                    seq        = payload.get("s")
                    event_type = payload.get("t")
                    data       = payload.get("d")
                    bump_event()
                    if seq is not None:
                        self.state["sequence"] = seq
                    if op == 0:
                        if event_type == "READY":
                            self.state["user_id"]   = data["user"]["id"]
                            self.state["username"]  = data["user"]["username"]
                            self.state["session_id"] = data.get("session_id")
                            cprint(f"[crime] logged in as {self.state['username']}")
                            self.cogs["presence"].restart_rotating(self.presence)
                            asyncio.create_task(self._business_loop())
                        elif event_type == "MESSAGE_CREATE":
                            asyncio.create_task(self.handle_message(data))
            finally:
                heartbeat_task.cancel()
                self.ws = None

    async def _business_loop(self):
        await self.cogs["presence"].business_hours_loop(self.presence)

    async def start(self):
        print_banner()
        await self.rest.start()
        credit_line = await fetch_credit_line(self.rest)
        print_credit_line(credit_line)
        asyncio.create_task(title_update_loop(lambda: self.state["username"]))
        try:
            while True:
                try:
                    await self.run_gateway()
                except (websockets.ConnectionClosed, OSError) as e:
                    cprint(f"[crime] gateway disconnected: {e}. reconnecting in 5s...")
                    await asyncio.sleep(5)
        finally:
            await self.rest.close()

if __name__ == "__main__":
    bot = CrimeBot()
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        cprint("[crime] shutting down...")