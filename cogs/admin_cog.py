import asyncio
import inspect
import os
from pathlib import Path
from collections import namedtuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial
from typing import Optional, Union, Awaitable, Callable

import discord
from discord.ext import commands

from cogs.base_cog import BaseCog, EmbedField
from config import TRUSTED_DIR, TRUSTED_PATH, YES_ARGS
from utils.access_control import (Categories, add_trusted_member,
                                  add_trusted_role, get_trusted_members,
                                  get_trusted_roles, remove_trusted_member,
                                  remove_trusted_role)
from utils.checks import admins_only, load_blacklist, save_blacklist
from utils.exceptions import CommandError



@dataclass
class Activity:
    text: str = ""
    callable_: Callable = None
    prepend_text: bool = True

    async def get_activity(self) -> str:
        r = ""
        if self.callable_:
            if inspect.iscoroutinefunction(self.callable_):
                r = await self.callable_()
            else:
                r = self.callable_()
        
        return f"{self.text}{r}" if self.prepend_text else f"{r}{self.text}"


class AdminCog(BaseCog):
    FILES = [TRUSTED_PATH]

    # Activity rotation stuff
    ACTIVITY_ROTATION = True
    AC_ROTATION_INTERVAL = 60

    """Admin commands for administering guild-related bot functionality."""
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Sets activity and prints a message when cog is instantiated 
        and added to the bot.
        """
        print("Bot logged in")
        await self.run_activity_rotation()

    async def run_activity_rotation(self) -> None:
        mc_cog = self.bot.get_cog("MinecraftCog")
        acitivities = [
            Activity(callable_=mc_cog.n_players_online),
        ]

        while self.ACTIVITY_ROTATION: 
            for activity in acitivities:
                await self._change_activity(await activity.get_activity())
                await asyncio.sleep(self.AC_ROTATION_INTERVAL)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Called when bot joins a guild."""
        await self.send_log(f"Joined guild {guild.name}", channel_id=self.GUILD_HISTORY_CHANNEL)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """Called when bot leaves a guild."""
        await self.send_log(f"Left guild {guild.name}", channel_id=self.GUILD_HISTORY_CHANNEL)

    async def _change_activity(self, activity_name: str) -> None:
        activity = discord.Game(activity_name)
        await self.bot.change_presence(activity=activity)

    @commands.command(name="serverlist")
    @admins_only()
    async def serverlist(self, ctx: commands.Context) -> None:
        """Sends a list of all guilds the bot is joined to."""
        guilds = "\n".join([guild.name for guild in self.bot.guilds])
        await self.send_embed_message(ctx, "Guilds", guilds)

    @commands.command(name="leave")
    @admins_only()
    async def leave(self, ctx: commands.Context, guild_id: int) -> None:
        """Attempts to leave a Discord Guild (server).
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord context
        guild_id : `int`
            ID of guild to leave.
        
        Raises
        ------
        `discord.DiscordException`
            Raised if a guild with ID `guild_id` cannot be found.
        `discord.DiscordException`
            Raised if bot is unable to leave the specified guild.
        """
        # Get discord.Guild object for guild with ID guild_id
        guild = self.bot.get_guild(int(guild_id))

        # Raise exception if guild is not found
        if not guild:
            return await ctx.send(f"No guild with ID {guild_id}")

        try:
            await guild.leave()
        except discord.HTTPException:
            raise discord.DiscordException(f"Unable to leave guild {guild.name}")
        else:
            await self.send_log(f"Left guild {guild.name} successfully")

    @commands.command(name="announce",
                      aliases=["send_all", "broadcast"])
    @admins_only()
    async def sendtoall(self, ctx: commands.Context, *msg) -> None:
        """
        Attempts to send text message to every server the bot
        is a member of.
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord context
        msg: `tuple`
            String to send.
        """
        msg = " ".join(msg)
        guilds = self.bot.guilds
        for guild in guilds:
            channel = guild.text_channels[0]
            try:
                await channel.send(message)
            except:
                # CBA spamming log channel with every message attempt
                print(f"Failed to send message to guild {guild.name}")

    @commands.group(name="log", aliases=["logs"])
    async def log(self, ctx: commands.Context) -> None:
        if not ctx.invoked_subcommand:
            raise CommandError("A subcommand is required!")

    def _get_log_dir(self) -> None:
        try:
            immortal_dir = os.environ["IMMORTAL_SDIR"]
        except KeyError:
            raise CommandError("Immortal SDIR environment variable is not set!")

        # Check if log dir exists
        log_dir = Path(immortal_dir) / "logs"
        if not log_dir.exists():
            raise CommandError("Unable to locate log directory!")
        
        return log_dir

    def get_log_file(self, log_name: Optional[str]) -> Path:
        if not log_name:
            log_name = "vjemmie.log" # Need to specify environ vars
        
        log_dir = self._get_log_dir()
        
        # Check if log file exists
        log = log_dir / log_name
        if not log.exists():
            raise CommandError(f"`{str(log)}` does not exist!")
        
        return log    

    @log.command(name="get")
    async def post_log(self, ctx: commands.Context, log_name: str=None, encoding: str="utf-8") -> None:
        """Print a log file in its entirety."""
        log = self.get_log_file(log_name)
        await self.read_send_file(ctx, log, encoding=encoding)

    @log.command(name="tail")
    async def post_log_tail(self, ctx: commands.Context, log_name: str=None, lines: int=5, encoding="utf8") -> None:
        """Print last N lines of a log file."""
        log = self.get_log_file(log_name)
        
        with open(log, "r", encoding=encoding) as f:
            _contents = f.read().splitlines()[-lines:]
        contents = "\n".join(_contents)
        
        await self.send_text_message(contents, ctx)

    @log.command(name="list")
    async def list_log_files(self, ctx: commands.Context) -> None:
        log_dir = self._get_log_dir()
        files = "\n".join(list(log_dir.iterdir()))
        await self.send_text_message(files, ctx)
