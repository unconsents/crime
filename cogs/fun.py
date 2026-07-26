import random
from core import (
    EIGHT_BALL, HACK_STEPS, UWU_MAP, FORTUNES, EMOJI_MAP,
    make_embed, uwuify, cprint
)
import pyfiglet

class FunCog:
    def __init__(self, bot):
        self.bot = bot

    async def handle(self, cmd, args, arg, channel_id, cfg):
        p = cfg["prefix"]

        if cmd == "8ball":
            if not arg:
                await self.bot.sad(channel_id, f"Usage: `{p}8ball <question>`"); return
            await self.bot.say(channel_id, make_embed("8-Ball", f"**Q:** {arg}\n**A:** {random.choice(EIGHT_BALL)}", footer=f"Usage: {p}8ball <question>"))

        elif cmd in ("coinflip", "flip"):
            await self.bot.say(channel_id, make_embed("Coin Flip", random.choice(["**Heads!**", "**Tails!**"]), footer=f"Usage: {p}coinflip"))

        elif cmd in ("dice", "roll"):
            count = min(int(args[0]), 10) if args and args[0].isdigit() else 1
            rolls = [random.randint(1, 6) for _ in range(count)]
            await self.bot.say(channel_id, make_embed("Dice Roll", f"Rolled {count}d6: **{', '.join(map(str,rolls))}**\nTotal: **{sum(rolls)}**", footer=f"Usage: {p}dice [count 1-10]"))

        elif cmd == "choose":
            opts = [o.strip() for o in arg.split(",") if o.strip()]
            if len(opts) < 2:
                await self.bot.sad(channel_id, f"Usage: `{p}choose option1, option2, ...` — provide at least 2 options"); return
            await self.bot.say(channel_id, make_embed("Choose", f"I choose: **{random.choice(opts)}**", footer=f"Usage: {p}choose option1, option2, ..."))

        elif cmd == "mock":
            if not arg:
                await self.bot.sad(channel_id, f"Usage: `{p}mock <text>`"); return
            mocked = "".join(c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(arg))
            await self.bot.say(channel_id, make_embed("Mock", mocked, footer=f"Usage: {p}mock <text>"))

        elif cmd == "reverse":
            if not arg:
                await self.bot.sad(channel_id, f"Usage: `{p}reverse <text>`"); return
            await self.bot.say(channel_id, make_embed("Reverse", arg[::-1], footer=f"Usage: {p}reverse <text>"))

        elif cmd == "ascii":
            if not arg:
                await self.bot.sad(channel_id, f"Usage: `{p}ascii <text>`"); return
            art = pyfiglet.figlet_format(arg[:20], font="standard").rstrip()
            await self.bot.say_text(channel_id, f"```\n{art}\n```")

        elif cmd == "emojify":
            if not arg:
                await self.bot.sad(channel_id, f"Usage: `{p}emojify <text>`"); return
            result = "".join(EMOJI_MAP.get(c.lower(), c) for c in arg)
            await self.bot.say(channel_id, make_embed("Emojify", result, footer=f"Usage: {p}emojify <text>"))

        elif cmd == "clap":
            if not arg:
                await self.bot.sad(channel_id, f"Usage: `{p}clap <text>`"); return
            await self.bot.say(channel_id, make_embed("Clap", " 👏 ".join(arg.split()), footer=f"Usage: {p}clap <text>"))

        elif cmd == "uwuify":
            if not arg:
                await self.bot.sad(channel_id, f"Usage: `{p}uwuify <text>`"); return
            await self.bot.say(channel_id, make_embed("uwu", uwuify(arg), footer=f"Usage: {p}uwuify <text>"))

        elif cmd == "ship":
            parts = [p2.strip() for p2 in arg.split(",")]
            if len(parts) < 2:
                await self.bot.sad(channel_id, f"Usage: `{p}ship name1, name2`"); return
            pct = random.randint(0, 100)
            bar = "💗" * (pct // 10) + "🖤" * (10 - pct // 10)
            await self.bot.say(channel_id, make_embed("Ship", f"**{parts[0]}** x **{parts[1]}**\n{bar}\n**{pct}% compatible!**", footer=f"Usage: {p}ship name1, name2"))

        elif cmd == "joke":
            data = await self.bot.rest.fetch_external("https://official-joke-api.appspot.com/random_joke")
            if not data:
                await self.bot.sad(channel_id, "Couldn't fetch a joke."); return
            await self.bot.say(channel_id, make_embed("Joke", f"{data['setup']}\n\n||{data['punchline']}||", footer=f"Usage: {p}joke"))

        elif cmd == "fact":
            data = await self.bot.rest.fetch_external("https://uselessfacts.jsph.pl/api/v2/facts/random?language=en")
            if not data:
                await self.bot.sad(channel_id, "Couldn't fetch a fact."); return
            await self.bot.say(channel_id, make_embed("Random Fact", data["text"], footer=f"Usage: {p}fact"))

        elif cmd == "quote":
            data = await self.bot.rest.fetch_external("https://api.quotable.io/random")
            if not data:
                await self.bot.sad(channel_id, "Couldn't fetch a quote."); return
            await self.bot.say(channel_id, make_embed("Quote", f'"{data["content"]}"\n— *{data["author"]}*', footer=f"Usage: {p}quote"))

        elif cmd == "fortune":
            await self.bot.say(channel_id, make_embed("Fortune", random.choice(FORTUNES), footer=f"Usage: {p}fortune"))

        elif cmd == "rate":
            if not arg:
                await self.bot.sad(channel_id, f"Usage: `{p}rate <thing>`"); return
            await self.bot.say(channel_id, make_embed("Rate", f"I rate **{arg}** a **{random.randint(0,100)}/100**!", footer=f"Usage: {p}rate <thing>"))

        elif cmd in ("howgay", "howcool", "howhot", "simprate", "ppsize"):
            labels = {"howgay":"gay","howcool":"cool","howhot":"hot","simprate":"simp","ppsize":"pp size"}
            label = labels[cmd]
            target = arg if arg else self.bot.state["username"]
            await self.bot.say(channel_id, make_embed(label.title(), f"**{target}** is **{random.randint(0,100)}%** {label}!", footer=f"Usage: {p}{cmd} [target]"))

        elif cmd == "hack":
            target = arg if arg else "unknown"
            steps_text = "\n".join(f"`{s}`" for s in HACK_STEPS)
            await self.bot.say(channel_id, make_embed(f"Hacking {target}...", steps_text, color=0x111111, footer=f"Usage: {p}hack [target]"))

        elif cmd == "cowsay":
            if not arg:
                await self.bot.sad(channel_id, f"Usage: `{p}cowsay <text>`"); return
            line = "-" * (len(arg) + 2)
            cow = f"```\n  {line}\n< {arg} >\n  {line}\n        \\   ^__^\n         \\  (oo)\\_______\n            (__)\\       )\\/\\\n                ||----w |\n                ||     ||\n```"
            await self.bot.say_text(channel_id, cow)

        else:
            return False
        return True
