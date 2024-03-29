import asyncio
import pickle
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from functools import partial
from collections import Counter
from itertools import islice
from pathlib import Path
from time import perf_counter, time, time_ns
from typing import List, Union, Dict, Tuple, Optional

import discord
from discord.ext import commands, tasks

from .base_cog import BaseCog
from ..utils.caching import get_cached
from ..utils.checks import owners_only
from ..utils.converters import UserOrMeConverter
from ..utils.exceptions import CommandError
from ..utils.datetimeutils import format_time_difference



@dataclass
class DiscordCommand:
    """Represents a Discord command. 
    
    Keeps track of total numbers of times the command is used 
    in a guild, as well as per-user statistics.
    """
    name: str = None
    times_used: int = 0
    users: Counter = field(init=False, default_factory=Counter)

    @property
    def top_user(self) -> Optional[Tuple[int, int]]:
        top_user = self.get_top_users(limit=1)
        return top_user.most_common() if top_user else None

    def log_command(self, ctx: commands.Context) -> None:
        self.times_used += 1
        self.users[ctx.message.author.id] += 1

    def get_top_users(self, limit: int) -> Counter:
        """Get users who have invoked the command the most often."""
        if not limit or limit < 0:
            limit = None
        return Counter(dict(self.users.most_common(limit)))


@dataclass
class DiscordGuild:
    ctx: commands.Context

    def __post_init__(self) -> None:
        self.guild_name = self.ctx.guild.name
        self.guild_id = self.ctx.guild.id
        self.commands = {}
        del self.ctx # has to be deleted so object can be pickled

    @property
    def top_total_commands_invokers(self) -> Counter:
        """Retrieves Counter of top command invokers in the guild."""
        users = Counter()
        for command in self.commands.values():
            for (uid, uses) in command.get_top_users(limit=None):
                users[uid] += uses
        return users

    def get_top_users_command(self, command: str, *, limit: int=None) -> Counter:
        """Get top N users of a command."""
        if not command in self.commands:
            # NOTE: should this really raise exception instead of returning empty list?
            raise AttributeError("Command has not been used in this server yet!")
        return self.commands[command].get_top_users(limit=limit)

    @property
    def top10_commands(self) -> Counter:
        """Get Counter of top 10 most used commands in the guild."""
        return self.get_top_commands(limit=10)

    def get_top_commands(self, limit: int=10) -> Counter:
        """Get Counter of top N most used commands in the guild."""
        top_commands = [(command.name, command.times_used) for command in self.commands.values()]

        if limit:
            top_commands = top_commands[:limit]

        return Counter(dict(top_commands))

    def log_command(self, ctx: commands.Context) -> None:
        """Log command usage."""
        if ctx.command.name not in self.commands:
            self.commands[ctx.command.name] = DiscordCommand(name=ctx.command.name)
        self.commands[ctx.command.name].log_command(ctx)


class StatsCog(BaseCog):
    """Commands and methods for gathering bot statistics."""

    EMOJI = ":chart_with_upwards_trend:"

    def __init__(self, bot: commands.Bot) -> None:
        self.statsfile = bot.config["paths"]["statsdir"] / "guilds.pkl"
        self.DIRS = [self.statsfile.parent]
        self.FILES = [self.statsfile]
        
        super().__init__(bot)
        self.bot.start_time = datetime.now()
        self.guilds = self.load_guilds()
        self.dump_command_stats.start()

    def cog_unload(self):
        self.dump_command_stats.cancel()
    
    def dump_guilds(self) -> None:
        """Save guild usage statistics."""
        with open(self.statsfile, "wb") as f:
            pickle.dump(self.guilds, f, protocol=pickle.HIGHEST_PROTOCOL)

    async def _do_dump(self) -> None:
        await self.bot.loop.run_in_executor(None, self.dump_guilds)

    @tasks.loop(seconds=300.0)
    async def dump_command_stats(self) -> None:
        await self._do_dump()

    @dump_command_stats.after_loop
    async def on_dump_command_stats_cancel(self) -> None:
        """Make sure we dump most recent stats if we are being cancelled."""
        if self.dump_command_stats.is_being_cancelled():
            await self._do_dump()

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context) -> None:
        self.log_command_usage(ctx)

    def log_command_usage(self, ctx: commands.Context) -> None:
        gid = ctx.guild.id
        if not self.guilds.get(gid):
            self.guilds[gid] = DiscordGuild(ctx)
        self.guilds[gid].log_command(ctx)

    def load_guilds(self) -> Dict[int, DiscordGuild]:
        """Load guild statistics. Only performed on bot startup."""
        with open(self.statsfile, "rb") as f:
            try:
                return pickle.load(f)
            except EOFError:
                return {}
            except:
                # Create backup if file isn't empty
                contents = f.read()
                if contents != {}:
                    with open(f"{self.statsfile}_{time_ns()}.bak", "wb") as backup:
                        backup.write(contents)
                return {}

    def get_top_commands_for_guild(self, guild_id: int, limit: int=0) -> Counter:
        """Get top commands for a specific guild."""
        return self.guilds[guild_id].get_top_commands(limit=limit)

    def get_top_commands_for_user(self, guild_id: int, user: discord.User, limit: int=0) -> Counter: # FIX
        """Get a Counter of a user's most used commands."""
        guild = self.guilds[guild_id]
        cmds = []
        for command in guild.commands.values():
            for user_id, used in command.users.items():
                if user_id == user.id:
                    cmds.append((command.name, used))
                    break
        if limit:
            cmds = cmds[:limit]
        return Counter(dict(cmds))

    def get_top_command_users(self, guild_id: int, command: str, limit: int=10) -> Counter:
        """Get top users of a specific command."""
        try:
            guild = self.guilds[guild_id]
            cmd = guild.commands[command]
        except KeyError: # Catches exception from both statements in 'try' clause
            return Counter()
        else:
            return cmd.get_top_users(limit=limit)

    def get_command_usage(self, guild_id: Union[str, int], command: str) -> int:
        """Get number of times a command has been used in a specific guild."""
        try:
            return self.guilds[guild_id].commands[command].times_used
        except KeyError:
            return 0

    @commands.command(name="topcommands", aliases=["topc"], usage="[user]")
    async def top_commands(self, ctx: commands.Context, user: UserOrMeConverter=None) -> None:
        """List most used commands in the server."""
        if not ctx.guild:
            raise CommandError("This command is not supported in DMs!")

        if user:
            cmds = self.get_top_commands_for_user(ctx.guild.id, user)
            if not cmds:
                raise CommandError("User has not used any commands yet!")
            title = f"Top commands for {user.name}"
        else:
            try:
                cmds = self.get_top_commands_for_guild(guild_id=ctx.guild.id)
            except:
                raise CommandError("No commands have been used in this server!")
            else:
                title = f"Top Commands for {ctx.guild.name}"

        # don't include commands that have been deleted or are unavailable      
        for command in list(cmds):
            if not self.bot.get_command(command):
                cmds.pop(command)
        
        # Create message body
        description = "\n".join([
            f"`{self.bot.command_prefix}{cmd.ljust(20, self.EMBED_FILL_CHAR)}:` {used}"
            for (cmd, used) in cmds.most_common(10)
        ])

        await self.send_embed_message(ctx, title=title, description=description)

    @commands.command(name="uptime", aliases=["up"])
    async def uptime(self, ctx: commands.Context) -> None:
        """Bot uptime."""
        up = self.get_bot_uptime(type=str)
        await ctx.send(f"Bot has been up for {up}")

    def get_bot_uptime(self, type: Union[dict, str]=dict) -> Union[dict, str]:
        up = format_time_difference(self.bot.start_time)
        if type == dict:
            return up
        elif type == str:
            up_fmt = lambda dur, unit: f"{dur}{unit} " if dur else ""
            uptime = (f"{up_fmt(up['days'], 'd')}"
                    f"{up_fmt(up['hours'], 'h')}"
                    f"{up_fmt(up['minutes'], 'm')}"
                    f"{up_fmt(up['seconds'], 's')}")
            return uptime
        else:
            raise TypeError("Return type must be 'str' or 'dict'")

    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context) -> str:
        ping_ms = self.get_bot_ping_ms()
        await ctx.send(f"Ping: {ping_ms}ms")

    def get_bot_ping_ms(self) -> int:
        return round(self.bot.ws.latency*100)
