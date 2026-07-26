import aiohttp
from core import make_embed, uptime_str

class UtilsCog:
    def __init__(self, bot):
        self.bot = bot

    async def handle(self, cmd, args, arg, channel_id, guild_id, cfg):
        p = cfg["prefix"]

        if cmd == "ping":
            await self.bot.say(channel_id, make_embed("Pong!", "crime is alive.", footer=f"Usage: {p}ping"))

        elif cmd == "avatar":
            uid = args[0].strip("<@!>") if args else self.bot.state["user_id"]
            user = await self.bot.rest.get_user(uid)
            if not user:
                await self.bot.sad(channel_id, f"User not found.\nUsage: `{p}avatar [@user]`"); return
            avatar_url = f"https://cdn.fluxer.app/avatars/{user['id']}/{user.get('avatar')}.png" if user.get("avatar") else None
            await self.bot.say(channel_id, make_embed("Avatar", f"Avatar for **{user.get('username','Unknown')}**", footer=f"Usage: {p}avatar [@user]", image_url=avatar_url))

        elif cmd == "userinfo":
            uid = args[0].strip("<@!>") if args else self.bot.state["user_id"]
            user = await self.bot.rest.get_user(uid)
            if not user:
                await self.bot.sad(channel_id, f"User not found.\nUsage: `{p}userinfo [@user]`"); return
            await self.bot.say(channel_id, make_embed("User Info", None, fields=[
                {"name": "ID",       "value": user.get("id","?"),          "inline": True},
                {"name": "Username", "value": user.get("username","?"),    "inline": True},
                {"name": "Bot",      "value": str(user.get("bot",False)),  "inline": True},
            ], footer=f"Usage: {p}userinfo [@user]"))

        elif cmd == "serverinfo":
            if not guild_id:
                await self.bot.sad(channel_id, f"Must be used in a server.\nUsage: `{p}serverinfo`"); return
            guild = await self.bot.rest.get_guild(guild_id)
            if not guild:
                await self.bot.sad(channel_id, "Could not fetch server info."); return
            await self.bot.say(channel_id, make_embed(f"{guild.get('name','Server')} Info", guild.get("description"), fields=[
                {"name": "ID",      "value": guild.get("id","?"),                      "inline": True},
                {"name": "Owner",   "value": guild.get("owner_id","?"),               "inline": True},
                {"name": "Members", "value": str(guild.get("member_count","?")),      "inline": True},
            ], footer=f"Usage: {p}serverinfo"))

        elif cmd == "channelinfo":
            ch = await self.bot.rest.get_channel(channel_id)
            if not ch:
                await self.bot.sad(channel_id, f"Could not fetch channel info.\nUsage: `{p}channelinfo`"); return
            await self.bot.say(channel_id, make_embed(f"#{ch.get('name','channel')} Info", ch.get("topic"), fields=[
                {"name": "ID",   "value": ch.get("id","?"),           "inline": True},
                {"name": "Type", "value": str(ch.get("type","?")),    "inline": True},
                {"name": "NSFW", "value": str(ch.get("nsfw",False)),  "inline": True},
            ], footer=f"Usage: {p}channelinfo"))

        elif cmd == "afk":
            self.bot.state["afk_active"] = True
            self.bot.state["afk_reason"] = arg if arg else "AFK"
            await self.bot.say(channel_id, make_embed("AFK", f"You are now AFK: **{self.bot.state['afk_reason']}**", footer=f"Usage: {p}afk [reason]"))

        elif cmd == "back":
            if self.bot.state["afk_active"]:
                self.bot.state["afk_active"] = False
                await self.bot.say(channel_id, make_embed("Welcome Back", "AFK status cleared.", footer=f"Usage: {p}back"))

        elif cmd == "calc":
            if not arg:
                await self.bot.sad(channel_id, f"Usage: `{p}calc <expression>`"); return
            if not all(c in "0123456789+-*/()., %" for c in arg):
                await self.bot.sad(channel_id, f"Invalid characters.\nUsage: `{p}calc <expression>` (numbers and + - * / ( ) . , % only)"); return
            result = eval(arg, {"__builtins__": {}})
            await self.bot.say(channel_id, make_embed("Calculator", f"`{arg}` = **{result}**", footer=f"Usage: {p}calc <expression>"))

        elif cmd == "urban":
            if not arg:
                await self.bot.sad(channel_id, f"Usage: `{p}urban <word>`"); return
            data = await self.bot.rest.fetch_external(f"https://api.urbandictionary.com/v0/define?term={aiohttp.helpers.quote(arg)}")
            if not data or not data.get("list"):
                await self.bot.sad(channel_id, f"No results found.\nUsage: `{p}urban <word>`"); return
            e = data["list"][0]
            await self.bot.say(channel_id, make_embed(e["word"], e["definition"][:800], fields=[
                {"name": "Example", "value": e.get("example","N/A")[:400] or "N/A", "inline": False}
            ], footer=f"{e.get('thumbs_up',0)} likes | Usage: {p}urban <word>"))

        elif cmd in ("wikipedia", "wiki"):
            if not arg:
                await self.bot.sad(channel_id, f"Usage: `{p}wiki <query>`"); return
            data = await self.bot.rest.fetch_external(f"https://en.wikipedia.org/api/rest_v1/page/summary/{aiohttp.helpers.quote(arg.replace(' ','_'))}")
            if not data or "title" not in data:
                await self.bot.sad(channel_id, f"Article not found.\nUsage: `{p}wiki <query>`"); return
            await self.bot.say(channel_id, make_embed(data.get("title","Wikipedia"), data.get("extract","")[:800], footer=f"Wikipedia | Usage: {p}wiki <query>"))

        else:
            return False
        return True
