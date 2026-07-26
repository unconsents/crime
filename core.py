import asyncio
import datetime
import json
import os
import time

import aiohttp
import colorama
import pyfiglet
import pytz
import websockets

colorama.init()

CONFIG_FILE = "crime_config.json"
PRESENCE_FILE = "crime_presence.json"

DEFAULT_CONFIG = {
    "token": "YOUR_TOKEN_HERE",
    "prefix": "!",
}

DEFAULT_PRESENCE = {
    "status": "online",
    "custom_status": None,
    "business_hours_enabled": False,
    "timezone": "UTC",
    "online_start": "08:00",
    "online_end": "17:00",
    "idle_before": "07:00",
    "idle_after": "18:00",
    "rotating_enabled": False,
    "rotating_statuses": [],
    "rotating_interval": 5,
}

API_BASE = "https://web.fluxer.app/api/v1"
GATEWAY_WS_URL = "wss://gateway.fluxer.app"
AUTO_DELETE_SECONDS = 10
AFK_REPLY_MIN_INTERVAL_SECONDS = 45
START_TIME = time.monotonic()

PERMISSION_BITS = {
    "kick":         0x00000002,
    "ban":          0x00000004,
    "manage_msgs":  0x00002000,
    "manage_roles": 0x10000000,
    "admin":        0x00000008,
    "timeout":      0x10000000,
}

STATUS_CHOICES = {"online", "idle", "dnd", "invisible"}

EMOJI_MAP = {
    "a":"🇦","b":"🇧","c":"🇨","d":"🇩","e":"🇪","f":"🇫","g":"🇬",
    "h":"🇭","i":"🇮","j":"🇯","k":"🇰","l":"🇱","m":"🇲","n":"🇳",
    "o":"🇴","p":"🇵","q":"🇶","r":"🇷","s":"🇸","t":"🇹","u":"🇺",
    "v":"🇻","w":"🇼","x":"🇽","y":"🇾","z":"🇿","0":"0️⃣","1":"1️⃣",
    "2":"2️⃣","3":"3️⃣","4":"4️⃣","5":"5️⃣","6":"6️⃣","7":"7️⃣",
    "8":"8️⃣","9":"9️⃣"," ":"  ",
}

EIGHT_BALL = [
    "It is certain.", "It is decidedly so.", "Without a doubt.",
    "Yes, definitely.", "You may rely on it.", "As I see it, yes.",
    "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
    "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
    "Cannot predict now.", "Concentrate and ask again.",
    "Don't count on it.", "My reply is no.", "My sources say no.",
    "Outlook not so good.", "Very doubtful.",
]

HACK_STEPS = [
    "Initializing hack sequence...", "Bypassing firewall...",
    "Accessing mainframe...", "Downloading personal files...",
    "Cracking password hash...", "Uploading virus...",
    "Covering tracks...", "Hack complete. They never stood a chance.",
]

UWU_MAP = {"r": "w", "l": "w", "R": "W", "L": "W"}

FORTUNES = [
    "Good things come to those who wait.", "Today is your lucky day!",
    "A surprise is waiting for you.", "Keep your eyes open for opportunity.",
    "The stars align in your favour.", "Beware of false friends.",
    "Hard work pays off soon.", "Something wonderful is about to happen.",
]

COOLDOWNS_DEF = {
    "8ball": 2, "coinflip": 2, "dice": 2, "choose": 2, "mock": 2,
    "reverse": 2, "emojify": 2, "clap": 2, "ship": 2, "joke": 3,
    "fact": 3, "quote": 3, "fortune": 3, "rate": 2, "howgay": 2,
    "howcool": 2, "howhot": 2, "simprate": 2, "ppsize": 2,
    "hack": 5, "cowsay": 2, "calc": 2, "urban": 5, "wikipedia": 5,
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        data = json.load(open(CONFIG_FILE))
        for k, v in DEFAULT_CONFIG.items():
            if k not in data:
                data[k] = v
        return data
    _save_json(CONFIG_FILE, DEFAULT_CONFIG)
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    _save_json(CONFIG_FILE, cfg)

def load_presence():
    if os.path.exists(PRESENCE_FILE):
        data = json.load(open(PRESENCE_FILE))
        for k, v in DEFAULT_PRESENCE.items():
            if k not in data:
                data[k] = v
        return data
    _save_json(PRESENCE_FILE, DEFAULT_PRESENCE.copy())
    return DEFAULT_PRESENCE.copy()

def save_presence(p):
    _save_json(PRESENCE_FILE, p)

def _save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def cprint(text):
    print(f"\x1b[38;2;180;0;0m{text}\x1b[0m")

def uptime_str():
    secs = int(time.monotonic() - START_TIME)
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m}m {s}s"

def make_embed(title=None, description=None, color=0xCC0000, fields=None, footer=None, image_url=None):
    e = {"color": color}
    if title:       e["title"] = title
    if description: e["description"] = description
    if fields:      e["fields"] = fields
    if footer:      e["footer"] = {"text": footer}
    if image_url:   e["image"] = {"url": image_url}
    e["timestamp"] = datetime.datetime.utcnow().isoformat()
    return e

def has_permission(perms_int, *bits):
    if perms_int & PERMISSION_BITS["admin"]:
        return True
    return all(perms_int & b for b in bits)

def compute_permissions(member, guild_roles):
    role_ids = set(member.get("roles", []))
    perms = 0
    for r in guild_roles:
        if r["id"] in role_ids:
            perms |= int(r.get("permissions", 0))
    return perms

def parse_user_arg(arg):
    return arg.strip("<@!>") if arg else None

def parse_duration(s):
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    if s and s[-1] in units:
        try:
            return int(s[:-1]) * units[s[-1]]
        except ValueError:
            pass
    try:
        return int(s)
    except (ValueError, TypeError):
        return None

def parse_hhmm(s):
    h, m = s.split(":")
    return int(h), int(m)

def uwuify(text):
    out = "".join(UWU_MAP.get(c, c) for c in text)
    import random
    return f"{out} {random.choice(['UwU', 'OwO', '>w<', '^w^'])}"

def print_banner():
    art = pyfiglet.figlet_format("crime", font="slant").rstrip("\n")
    width = 60
    for line in art.split("\n"):
        print(f"\x1b[38;2;180;0;0m{line.center(width)}\x1b[0m")
    print(f"\x1b[38;2;120;120;120m{'made by unconsents#2167 | Version: 1.0.2 (release)':^{width}}\x1b[0m")
    print()

class FluxerREST:
    def __init__(self, token):
        self.token = token
        self.session = None

    async def start(self):
        self.session = aiohttp.ClientSession(headers={
            "Authorization": self.token,
            "Content-Type": "application/json",
            "Origin": "https://web.fluxer.app",
            "Referer": "https://web.fluxer.app/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) fluxer_app/0.0.8 Chrome/142.0.7444.235 Electron/39.2.7 Safari/537.36",
        })

    async def close(self):
        if self.session:
            await self.session.close()

    async def send(self, channel_id, content=None, embeds=None, reply_to=None):
        payload = {}
        if content:  payload["content"] = content
        if embeds:   payload["embeds"] = embeds if isinstance(embeds, list) else [embeds]
        if reply_to: payload["message_reference"] = {"message_id": reply_to}
        async with self.session.post(f"{API_BASE}/channels/{channel_id}/messages", json=payload) as resp:
            body = await resp.text()
            if resp.status not in (200, 201):
                cprint(f"[crime] send error {resp.status}: {body}")
                return None
            return json.loads(body)

    async def delete(self, channel_id, message_id):
        async with self.session.delete(f"{API_BASE}/channels/{channel_id}/messages/{message_id}") as resp:
            if resp.status not in (200, 204):
                cprint(f"[crime] delete error {resp.status}: {await resp.text()}")

    async def get_user(self, user_id):
        async with self.session.get(f"{API_BASE}/users/{user_id}") as resp:
            return await resp.json() if resp.status == 200 else None

    async def get_guild(self, guild_id):
        async with self.session.get(f"{API_BASE}/guilds/{guild_id}") as resp:
            return await resp.json() if resp.status == 200 else None

    async def get_channel(self, channel_id):
        async with self.session.get(f"{API_BASE}/channels/{channel_id}") as resp:
            return await resp.json() if resp.status == 200 else None

    async def get_me_member(self, guild_id):
        async with self.session.get(f"{API_BASE}/guilds/{guild_id}/members/@me") as resp:
            return await resp.json() if resp.status == 200 else None

    async def get_guild_roles(self, guild_id):
        async with self.session.get(f"{API_BASE}/guilds/{guild_id}/roles") as resp:
            return await resp.json() if resp.status == 200 else []

    async def kick(self, guild_id, user_id, reason=None):
        h = {"X-Audit-Log-Reason": reason} if reason else {}
        async with self.session.delete(f"{API_BASE}/guilds/{guild_id}/members/{user_id}", headers=h) as resp:
            return resp.status in (200, 204), await resp.text()

    async def ban(self, guild_id, user_id, reason=None, delete_days=0):
        h = {"X-Audit-Log-Reason": reason} if reason else {}
        async with self.session.put(f"{API_BASE}/guilds/{guild_id}/bans/{user_id}", json={"delete_message_days": delete_days}, headers=h) as resp:
            return resp.status in (200, 204), await resp.text()

    async def unban(self, guild_id, user_id, reason=None):
        h = {"X-Audit-Log-Reason": reason} if reason else {}
        async with self.session.delete(f"{API_BASE}/guilds/{guild_id}/bans/{user_id}", headers=h) as resp:
            return resp.status in (200, 204), await resp.text()

    async def timeout(self, guild_id, user_id, until_iso=None, reason=None):
        h = {"X-Audit-Log-Reason": reason} if reason else {}
        async with self.session.patch(f"{API_BASE}/guilds/{guild_id}/members/{user_id}", json={"communication_disabled_until": until_iso}, headers=h) as resp:
            return resp.status in (200, 204), await resp.text()

    async def purge(self, channel_id, message_ids):
        if len(message_ids) == 1:
            await self.delete(channel_id, message_ids[0])
            return True, ""
        async with self.session.post(f"{API_BASE}/channels/{channel_id}/messages/bulk-delete", json={"messages": message_ids}) as resp:
            return resp.status in (200, 204), await resp.text()

    async def get_messages(self, channel_id, limit=100):
        async with self.session.get(f"{API_BASE}/channels/{channel_id}/messages?limit={limit}") as resp:
            return await resp.json() if resp.status == 200 else []

    async def add_role(self, guild_id, user_id, role_id, reason=None):
        h = {"X-Audit-Log-Reason": reason} if reason else {}
        async with self.session.put(f"{API_BASE}/guilds/{guild_id}/members/{user_id}/roles/{role_id}", headers=h) as resp:
            return resp.status in (200, 204), await resp.text()

    async def remove_role(self, guild_id, user_id, role_id, reason=None):
        h = {"X-Audit-Log-Reason": reason} if reason else {}
        async with self.session.delete(f"{API_BASE}/guilds/{guild_id}/members/{user_id}/roles/{role_id}", headers=h) as resp:
            return resp.status in (200, 204), await resp.text()

    async def patch_user_settings(self, payload):
        async with self.session.patch(f"{API_BASE}/users/@me/settings", json=payload) as resp:
            return resp.status in (200, 204), await resp.text()

    async def fetch_external(self, url):
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as resp:
                if resp.status != 200:
                    return None
                ct = resp.headers.get("Content-Type", "")
                return await resp.json() if "json" in ct else await resp.text()