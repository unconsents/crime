import asyncio
import datetime
import itertools
import pytz
from core import (
    make_embed, cprint, save_presence, STATUS_CHOICES,
    parse_hhmm, API_BASE
)

class PresenceCog:
    def __init__(self, bot):
        self.bot = bot
        self._rotating_task = None

    def _business_status(self, p):
        try:
            tz = pytz.timezone(p.get("timezone", "UTC"))
        except Exception:
            tz = pytz.utc
        now = datetime.datetime.now(tz)
        cur = (now.hour, now.minute)
        idle_before  = parse_hhmm(p.get("idle_before",  "07:00"))
        online_start = parse_hhmm(p.get("online_start", "08:00"))
        online_end   = parse_hhmm(p.get("online_end",   "17:00"))
        idle_after   = parse_hhmm(p.get("idle_after",   "18:00"))
        if online_start <= cur < online_end:
            return "online"
        elif idle_before <= cur < online_start or online_end <= cur < idle_after:
            return "idle"
        return "dnd"

    def effective_status(self, p):
        if p.get("business_hours_enabled"):
            return self._business_status(p)
        return p.get("status", "online")

    async def push_status(self, p, status_override=None):
        status = status_override or self.effective_status(p)
        ok, body = await self.bot.rest.patch_user_settings({"status": status})
        if not ok:
            cprint(f"[crime] status update failed: {body}")
        return ok

    async def push_custom_status(self, p, text_override="__unset__"):
        text = p.get("custom_status") if text_override == "__unset__" else text_override
        payload = {"custom_status": {"text": text, "expires_at": None} if text else None}
        ok, body = await self.bot.rest.patch_user_settings(payload)
        if not ok:
            cprint(f"[crime] custom status update failed: {body}")
        return ok

    async def business_hours_loop(self, p):
        last = None
        while True:
            if p.get("business_hours_enabled"):
                s = self._business_status(p)
                if s != last:
                    last = s
                    cprint(f"[crime] business hours -> {s}")
                    await self.push_status(p, s)
            await asyncio.sleep(30)

    async def rotating_loop(self, p):
        statuses = p.get("rotating_statuses", [])
        interval = max(1, p.get("rotating_interval", 5))
        if not statuses:
            return
        for text in itertools.cycle(statuses):
            if not p.get("rotating_enabled"):
                break
            await self.push_custom_status(p, text)
            await asyncio.sleep(interval)

    def restart_rotating(self, p):
        if self._rotating_task and not self._rotating_task.done():
            self._rotating_task.cancel()
        if p.get("rotating_enabled") and p.get("rotating_statuses"):
            self._rotating_task = asyncio.create_task(self.rotating_loop(p))

    async def handle(self, cmd, args, arg, channel_id, cfg):
        p = cfg["prefix"]
        pres = self.bot.presence

        if cmd == "presence":
            enabled = "enabled" if pres.get("business_hours_enabled") else "disabled"
            rot = "enabled" if pres.get("rotating_enabled") else "disabled"
            await self.bot.say(channel_id, make_embed("Presence", f"Usage: `{p}presence` — shows current settings", fields=[
                {"name": "Status",          "value": self.effective_status(pres),       "inline": True},
                {"name": "Custom Status",   "value": pres.get("custom_status") or "none", "inline": True},
                {"name": "Business Hours",  "value": enabled,                           "inline": True},
                {"name": "Timezone",        "value": pres.get("timezone","UTC"),        "inline": True},
                {"name": "Rotating Status", "value": rot,                               "inline": True},
                {"name": "Rotate Interval", "value": f"{pres.get('rotating_interval',5)}s", "inline": True},
            ], footer="crime selfbot"))

        elif cmd == "status":
            if pres.get("business_hours_enabled"):
                await self.bot.sad(channel_id, f"Business hours is on — status is set automatically.\nUse `{p}businesshours off` first."); return True
            if not args or args[0].lower() not in STATUS_CHOICES:
                await self.bot.sad(channel_id, f"Usage: `{p}status <{'|'.join(sorted(STATUS_CHOICES))}>`\nCurrent: `{pres.get('status','online')}`"); return True
            new = args[0].lower()
            ok = await self.push_status(pres, new)
            if ok:
                pres["status"] = new
                save_presence(pres)
                await self.bot.say(channel_id, make_embed("✅ Status", f"Status set to `{new}`.", footer=f"Usage: {p}status <online|idle|dnd|invisible>"))
            else:
                await self.bot.sad(channel_id, "Could not update status. Check terminal for details.")

        elif cmd == "customstatus":
            if not arg:
                await self.bot.sad(channel_id, f"Usage: `{p}customstatus <text>` or `{p}customstatus clear`"); return True
            if arg.lower() == "clear":
                ok = await self.push_custom_status(pres, None)
                if ok:
                    pres["custom_status"] = None
                    save_presence(pres)
                    await self.bot.say(channel_id, make_embed("✅ Custom Status", "Custom status cleared.", footer=f"Usage: {p}customstatus <text|clear>"))
                else:
                    await self.bot.sad(channel_id, "Could not clear custom status.")
                return True
            ok = await self.push_custom_status(pres, arg)
            if ok:
                pres["custom_status"] = arg
                save_presence(pres)
                await self.bot.say(channel_id, make_embed("✅ Custom Status", f"Custom status set to: **{arg}**", footer=f"Usage: {p}customstatus <text|clear>"))
            else:
                await self.bot.sad(channel_id, "Could not set custom status.")

        elif cmd == "rotatingstatus":
            sub = args[0].lower() if args else "info"

            if sub == "on":
                if not pres.get("rotating_statuses"):
                    await self.bot.sad(channel_id, f"No statuses in the list. Add some with `{p}rotatingstatus add <text>` first."); return True
                pres["rotating_enabled"] = True
                save_presence(pres)
                self.restart_rotating(pres)
                await self.bot.say(channel_id, make_embed("✅ Rotating Status", "Rotating status enabled.", footer=f"Usage: {p}rotatingstatus on"))

            elif sub == "off":
                pres["rotating_enabled"] = False
                save_presence(pres)
                self.restart_rotating(pres)
                await self.bot.say(channel_id, make_embed("✅ Rotating Status", "Rotating status disabled.", footer=f"Usage: {p}rotatingstatus off"))

            elif sub == "add":
                text = " ".join(args[1:])
                if not text:
                    await self.bot.sad(channel_id, f"Usage: `{p}rotatingstatus add <text>`"); return True
                pres["rotating_statuses"].append(text)
                save_presence(pres)
                count = len(pres["rotating_statuses"])
                await self.bot.say(channel_id, make_embed("✅ Rotating Status", f"Added: **{text}**\nTotal statuses: **{count}**", footer=f"Usage: {p}rotatingstatus add <text>"))

            elif sub == "remove":
                if len(args) < 2 or not args[1].isdigit():
                    await self.bot.sad(channel_id, f"Usage: `{p}rotatingstatus remove <index>`\nUse `{p}rotatingstatus list` to see indexes."); return True
                idx = int(args[1]) - 1
                statuses = pres["rotating_statuses"]
                if not (0 <= idx < len(statuses)):
                    await self.bot.sad(channel_id, f"Index out of range. Use `{p}rotatingstatus list` to see valid indexes."); return True
                removed = statuses.pop(idx)
                save_presence(pres)
                await self.bot.say(channel_id, make_embed("✅ Rotating Status", f"Removed: **{removed}**", footer=f"Usage: {p}rotatingstatus remove <index>"))

            elif sub == "clear":
                pres["rotating_statuses"] = []
                pres["rotating_enabled"] = False
                save_presence(pres)
                self.restart_rotating(pres)
                await self.bot.say(channel_id, make_embed("✅ Rotating Status", "All rotating statuses cleared.", footer=f"Usage: {p}rotatingstatus clear"))

            elif sub == "list":
                statuses = pres.get("rotating_statuses", [])
                if not statuses:
                    await self.bot.say(channel_id, make_embed("Rotating Status", "No statuses in the list.", footer=f"Usage: {p}rotatingstatus add <text>")); return True
                listed = "\n".join(f"`{i+1}.` {s}" for i, s in enumerate(statuses))
                await self.bot.say(channel_id, make_embed("Rotating Status List", listed, footer=f"Usage: {p}rotatingstatus list"))

            elif sub == "interval":
                if len(args) < 2 or not args[1].isdigit():
                    await self.bot.sad(channel_id, f"Usage: `{p}rotatingstatus interval <seconds>`\nCurrent: `{pres.get('rotating_interval',5)}s`"); return True
                secs = max(1, int(args[1]))
                pres["rotating_interval"] = secs
                save_presence(pres)
                self.restart_rotating(pres)
                await self.bot.say(channel_id, make_embed("✅ Rotating Status", f"Interval set to `{secs}s`.", footer=f"Usage: {p}rotatingstatus interval <seconds>"))

            else:
                rot = "enabled" if pres.get("rotating_enabled") else "disabled"
                count = len(pres.get("rotating_statuses", []))
                await self.bot.say(channel_id, make_embed("Rotating Status", None, fields=[
                    {"name": "State",      "value": rot,                                   "inline": True},
                    {"name": "Interval",   "value": f"{pres.get('rotating_interval',5)}s", "inline": True},
                    {"name": "Count",      "value": str(count),                            "inline": True},
                ], footer=f"Subcommands: on, off, add, remove, clear, list, interval"))

        elif cmd == "businesshours":
            sub = args[0].lower() if args else "info"

            if sub == "on":
                pres["business_hours_enabled"] = True
                save_presence(pres)
                await self.bot.say(channel_id, make_embed("✅ Business Hours", "Business hours scheduling enabled.", footer=f"Usage: {p}businesshours on"))

            elif sub == "off":
                pres["business_hours_enabled"] = False
                save_presence(pres)
                await self.bot.say(channel_id, make_embed("✅ Business Hours", "Business hours scheduling disabled.", footer=f"Usage: {p}businesshours off"))

            elif sub == "timezone":
                if len(args) < 2:
                    await self.bot.sad(channel_id, f"Usage: `{p}businesshours timezone <tz>`\nExample: `America/New_York`, `Europe/London`, `Asia/Beirut`\nCurrent: `{pres.get('timezone','UTC')}`"); return True
                tz_name = args[1]
                try:
                    pytz.timezone(tz_name)
                except pytz.UnknownTimeZoneError:
                    await self.bot.sad(channel_id, f"Unknown timezone `{tz_name}`.\nUsage: `{p}businesshours timezone <tz>` — use a valid tz name e.g. `Asia/Beirut`"); return True
                pres["timezone"] = tz_name
                save_presence(pres)
                await self.bot.say(channel_id, make_embed("✅ Business Hours", f"Timezone set to `{tz_name}`.", footer=f"Usage: {p}businesshours timezone <tz>"))

            elif sub == "setonline":
                if len(args) < 3:
                    await self.bot.sad(channel_id, f"Usage: `{p}businesshours setonline <HH:MM> <HH:MM>`\nCurrent: `{pres.get('online_start')}` - `{pres.get('online_end')}`"); return True
                pres["online_start"] = args[1]
                pres["online_end"] = args[2]
                save_presence(pres)
                await self.bot.say(channel_id, make_embed("✅ Business Hours", f"Online window: `{args[1]}` - `{args[2]}`", footer=f"Usage: {p}businesshours setonline HH:MM HH:MM"))

            elif sub == "setidle":
                if len(args) < 3:
                    await self.bot.sad(channel_id, f"Usage: `{p}businesshours setidle <HH:MM> <HH:MM>`\nCurrent before: `{pres.get('idle_before')}` / after: `{pres.get('idle_after')}`"); return True
                pres["idle_before"] = args[1]
                pres["idle_after"] = args[2]
                save_presence(pres)
                await self.bot.say(channel_id, make_embed("✅ Business Hours", f"Idle buffer: `{args[1]}` before / `{args[2]}` after online.", footer=f"Usage: {p}businesshours setidle HH:MM HH:MM"))

            else:
                enabled = "enabled" if pres.get("business_hours_enabled") else "disabled"
                current = self._business_status(pres) if pres.get("business_hours_enabled") else "n/a"
                await self.bot.say(channel_id, make_embed("Business Hours", None, fields=[
                    {"name": "Enabled",     "value": enabled,                                              "inline": True},
                    {"name": "Timezone",    "value": pres.get("timezone","UTC"),                          "inline": True},
                    {"name": "Current",     "value": current,                                             "inline": True},
                    {"name": "Online",      "value": f"{pres.get('online_start')} - {pres.get('online_end')}", "inline": True},
                    {"name": "Idle before", "value": pres.get("idle_before"),                             "inline": True},
                    {"name": "Idle after",  "value": pres.get("idle_after"),                              "inline": True},
                ], footer=f"Subcommands: on, off, timezone, setonline, setidle"))

        else:
            return False
        return True
