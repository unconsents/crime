from core import make_embed, uptime_str, save_config, cprint

class MiscCog:
    def __init__(self, bot):
        self.bot = bot

    async def handle(self, cmd, args, arg, channel_id, cfg):
        p = cfg["prefix"]

        if cmd == "help":
            categories = {
                "Fun":        "8ball, coinflip, dice, choose, mock, reverse, ascii, emojify, clap, uwuify, ship, joke, fact, quote, fortune, rate, howgay, howcool, howhot, simprate, ppsize, hack, cowsay",
                "Utils":      "ping, avatar, userinfo, serverinfo, channelinfo, afk, back, calc, urban, wiki",
                "Moderation": "kick, ban, unban, timeout, untimeout, purge, addrole, removerole",
                "Presence":   "presence, status, customstatus, businesshours, rotatingstatus",
                "Misc":       "help, about, version, uptime, prefix",
            }
            await self.bot.say(channel_id, make_embed("crime Commands", f"Prefix: `{p}`", fields=[
                {"name": cat, "value": f"`{cmds}`", "inline": False}
                for cat, cmds in categories.items()
            ], footer=f"Usage: {p}help"))

        elif cmd == "about":
            await self.bot.say(channel_id, make_embed("About crime", "**crime** is a raw selfbot for Fluxer.", fields=[
                {"name": "Prefix",  "value": p,           "inline": True},
                {"name": "Uptime",  "value": uptime_str(), "inline": True},
                {"name": "Version", "value": "v1.0.0",    "inline": True},
            ], footer=f"Usage: {p}about"))

        elif cmd == "version":
            await self.bot.say(channel_id, make_embed("Version", "crime **v1.0.0**", footer=f"Usage: {p}version"))

        elif cmd == "uptime":
            await self.bot.say(channel_id, make_embed("Uptime", f"crime has been running for **{uptime_str()}**.", footer=f"Usage: {p}uptime"))

        elif cmd == "prefix":
            if not arg:
                await self.bot.say(channel_id, make_embed("Prefix", f"Current prefix: `{p}`", footer=f"Usage: {p}prefix [new_prefix]")); return True
            cfg["prefix"] = arg.strip()
            save_config(cfg)
            cprint(f"[crime] prefix changed to: {cfg['prefix']}")
            await self.bot.say(channel_id, make_embed("✅ Prefix Updated", f"Prefix changed to `{cfg['prefix']}`", footer=f"Usage: {cfg['prefix']}prefix [new_prefix]"))

        else:
            return False
        return True
