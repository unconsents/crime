import datetime
from core import (
    make_embed, has_permission, compute_permissions,
    parse_user_arg, parse_duration, PERMISSION_BITS
)

class ModerationCog:
    def __init__(self, bot):
        self.bot = bot

    async def _perms(self, guild_id, bit_key):
        me = await self.bot.rest.get_me_member(guild_id)
        roles = await self.bot.rest.get_guild_roles(guild_id)
        perms = compute_permissions(me, roles) if me else 0
        return has_permission(perms, PERMISSION_BITS[bit_key])

    async def handle(self, cmd, args, arg, channel_id, guild_id, cfg):
        p = cfg["prefix"]

        if not guild_id:
            await self.bot.sad(channel_id, "This command must be used in a server."); return True

        if cmd == "kick":
            if not args:
                await self.bot.sad(channel_id, f"Usage: `{p}kick <@user> [reason]`"); return True
            if not await self._perms(guild_id, "kick"):
                await self.bot.sad(channel_id, "❌ Missing permission: Kick Members"); return True
            uid = parse_user_arg(args[0])
            reason = " ".join(args[1:]) or "No reason provided"
            ok, body = await self.bot.rest.kick(guild_id, uid, reason)
            if ok:
                await self.bot.say(channel_id, make_embed("✅ Kicked", f"<@{uid}> was kicked.\n**Reason:** {reason}", footer=f"Usage: {p}kick <@user> [reason]"))
            else:
                await self.bot.sad(channel_id, f"Could not kick user.\n`{body}`")

        elif cmd == "ban":
            if not args:
                await self.bot.sad(channel_id, f"Usage: `{p}ban <@user> [reason]`"); return True
            if not await self._perms(guild_id, "ban"):
                await self.bot.sad(channel_id, "❌ Missing permission: Ban Members"); return True
            uid = parse_user_arg(args[0])
            reason = " ".join(args[1:]) or "No reason provided"
            ok, body = await self.bot.rest.ban(guild_id, uid, reason)
            if ok:
                await self.bot.say(channel_id, make_embed("✅ Banned", f"<@{uid}> was banned.\n**Reason:** {reason}", footer=f"Usage: {p}ban <@user> [reason]"))
            else:
                await self.bot.sad(channel_id, f"Could not ban user.\n`{body}`")

        elif cmd == "unban":
            if not args:
                await self.bot.sad(channel_id, f"Usage: `{p}unban <user_id> [reason]`"); return True
            if not await self._perms(guild_id, "ban"):
                await self.bot.sad(channel_id, "❌ Missing permission: Ban Members"); return True
            uid = args[0].strip()
            reason = " ".join(args[1:]) or "No reason provided"
            ok, body = await self.bot.rest.unban(guild_id, uid, reason)
            if ok:
                await self.bot.say(channel_id, make_embed("✅ Unbanned", f"<@{uid}> was unbanned.\n**Reason:** {reason}", footer=f"Usage: {p}unban <user_id> [reason]"))
            else:
                await self.bot.sad(channel_id, f"Could not unban user.\n`{body}`")

        elif cmd in ("timeout", "mute"):
            if len(args) < 2:
                await self.bot.sad(channel_id, f"Usage: `{p}timeout <@user> <duration> [reason]`\nDuration: `10s`, `5m`, `2h`, `1d`"); return True
            if not await self._perms(guild_id, "timeout"):
                await self.bot.sad(channel_id, "❌ Missing permission: Moderate Members"); return True
            uid = parse_user_arg(args[0])
            secs = parse_duration(args[1])
            if not secs:
                await self.bot.sad(channel_id, f"Invalid duration. Use e.g. `30s`, `5m`, `1h`, `1d`.\nUsage: `{p}timeout <@user> <duration> [reason]`"); return True
            reason = " ".join(args[2:]) or "No reason provided"
            until = (datetime.datetime.utcnow() + datetime.timedelta(seconds=secs)).isoformat() + "Z"
            ok, body = await self.bot.rest.timeout(guild_id, uid, until, reason)
            if ok:
                await self.bot.say(channel_id, make_embed("✅ Timed Out", f"<@{uid}> timed out for `{args[1]}`.\n**Reason:** {reason}", footer=f"Usage: {p}timeout <@user> <duration> [reason]"))
            else:
                await self.bot.sad(channel_id, f"Could not timeout user.\n`{body}`")

        elif cmd in ("untimeout", "unmute"):
            if not args:
                await self.bot.sad(channel_id, f"Usage: `{p}untimeout <@user>`"); return True
            if not await self._perms(guild_id, "timeout"):
                await self.bot.sad(channel_id, "❌ Missing permission: Moderate Members"); return True
            uid = parse_user_arg(args[0])
            ok, body = await self.bot.rest.timeout(guild_id, uid, None)
            if ok:
                await self.bot.say(channel_id, make_embed("✅ Timeout Removed", f"<@{uid}>'s timeout was removed.", footer=f"Usage: {p}untimeout <@user>"))
            else:
                await self.bot.sad(channel_id, f"Could not remove timeout.\n`{body}`")

        elif cmd in ("purge", "clear"):
            count = int(args[0]) if args and args[0].isdigit() else None
            if not count or not (1 <= count <= 100):
                await self.bot.sad(channel_id, f"Usage: `{p}purge <1-100>`"); return True
            if not await self._perms(guild_id, "manage_msgs"):
                await self.bot.sad(channel_id, "❌ Missing permission: Manage Messages"); return True
            messages = await self.bot.rest.get_messages(channel_id, limit=count)
            ids = [m["id"] for m in messages]
            if not ids:
                await self.bot.sad(channel_id, "No messages found to delete."); return True
            ok, body = await self.bot.rest.purge(channel_id, ids)
            if ok:
                await self.bot.say(channel_id, make_embed("✅ Purged", f"Deleted **{len(ids)}** messages.", footer=f"Usage: {p}purge <1-100>"))
            else:
                await self.bot.sad(channel_id, f"Could not purge messages.\n`{body}`")

        elif cmd == "addrole":
            if len(args) < 2:
                await self.bot.sad(channel_id, f"Usage: `{p}addrole <@user> <role_id>`"); return True
            if not await self._perms(guild_id, "manage_roles"):
                await self.bot.sad(channel_id, "❌ Missing permission: Manage Roles"); return True
            uid = parse_user_arg(args[0])
            role_id = args[1].strip("<@&>")
            ok, body = await self.bot.rest.add_role(guild_id, uid, role_id)
            if ok:
                await self.bot.say(channel_id, make_embed("✅ Role Added", f"Added <@&{role_id}> to <@{uid}>.", footer=f"Usage: {p}addrole <@user> <role_id>"))
            else:
                await self.bot.sad(channel_id, f"Could not add role.\n`{body}`")

        elif cmd == "removerole":
            if len(args) < 2:
                await self.bot.sad(channel_id, f"Usage: `{p}removerole <@user> <role_id>`"); return True
            if not await self._perms(guild_id, "manage_roles"):
                await self.bot.sad(channel_id, "❌ Missing permission: Manage Roles"); return True
            uid = parse_user_arg(args[0])
            role_id = args[1].strip("<@&>")
            ok, body = await self.bot.rest.remove_role(guild_id, uid, role_id)
            if ok:
                await self.bot.say(channel_id, make_embed("✅ Role Removed", f"Removed <@&{role_id}> from <@{uid}>.", footer=f"Usage: {p}removerole <@user> <role_id>"))
            else:
                await self.bot.sad(channel_id, f"Could not remove role.\n`{body}`")

        else:
            return False
        return True
