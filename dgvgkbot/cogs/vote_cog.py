import inspect
import subprocess
from datetime import datetime
from functools import partial  # !!!!
from typing import Callable, Dict

import discord
from discord.ext import commands

from cogs.base_cog import BaseCog
from utils.exceptions import CommandError


class Vote:
    """Represents a voting session."""
    
    ACTION_MSG = ""
    SUCCESS_MSG = ""
    FAIL_MSG = ""
    
    def __init__(self, 
                 threshold: int, 
                 duration: float,
                 bot: commands.Bot,
                ) -> None:
        """
        Parameters
        ----------
        threshold : `int`
            Number of votes required to pass the vote.
        duration : `float`
            Duration of voting session in seconds.
        bot : `commands.Bot`
            Discord Bot instance
        """
        self.reset()     
        self.threshold = threshold
        self.duration = duration
        self.bot = bot
        # TODO: Add superuser vote weighting
        #       Add superuser supervote (triggers action)
    
    def reset(self) -> None:
        """Initializes voting session."""
        self.start = datetime.now()
        self.votes = {}

    @property
    def remaining(self) -> int:
        return self.threshold - len(self.votes)

    @property
    def current(self) -> int:
        return len(self.votes)

    @property
    def elapsed(self) -> float:
        return (datetime.now() - self.start).total_seconds()
    
    async def check_votes(self) -> bool:
        """Checks if sufficient votes are reached."""
        return len(self.votes) >= self.threshold    
    
    async def add_vote(self, ctx: commands.Context, action: bool=True) -> None:
        """Adds a vote. Performs action if enough votes are cast."""
        if self.elapsed < self.duration: # Check if voting session is active
            if not await self._vote_exists(ctx):
                await self._add_vote(ctx)
            else:
                return # this is a little messy
        else:
            self.reset() # reset voting session
            await self._add_vote(ctx)

        if await self.check_votes():
            try:
                await ctx.send(self.ACTION_MSG)
                await self.action()
            except:
                await ctx.send(self.FAIL_MSG)
                raise
            else:
                await ctx.send(self.SUCCESS_MSG)
        else:
            await ctx.send(f"Vote added! {self.remaining} more votes are required.")

    async def _add_vote(self, ctx: commands.Context) -> None:
        self.votes[ctx.message.author.id] = ctx.message.author

    async def _vote_exists(self, ctx: commands.Context) -> bool:
        """Check if voter has already voted. 
        Sends message to voter's channel if a previous vote exists."""
        if ctx.message.author.id in self.votes:
            minutes = self.duration//60
            if not minutes:
                time_msg = f"{int(self.duration)} seconds"
            else:
                time_msg = f"{round(minutes)} minute"
                if minutes > 1:
                    time_msg += "s"
            await ctx.send(
                f"You have already voted within the last {time_msg}."
            )
        return ctx.message.author.id in self.votes

    async def action(self) -> None:
        """Performs action. Subclasses need to define this method."""
        raise NotImplementedError

    async def can_do_action(self) -> None:
        """Check if sufficient votes are reached and that an action is defined."""
        return await self.check_votes() and self.action


class VoteServerStart(Vote):
    ACTION_MSG = "Starting server..."
    SUCCESS_MSG = "Server started."
    FAIL_MSG = "Failed to start server."

    async def action(self) -> None:
        """Starts Minecraft server."""
        r = subprocess.run(["immortalctl", "start", "mcserver"], check=True) 
        # param check raises exception if non-0 exit code
    

class VoteServerStop(Vote):
    ACTION_MSG = "Stopping server..."
    SUCCESS_MSG = "Server stopped."
    FAIL_MSG = "Failed to stop server. Is the server already down?"

    async def action(self) -> None:
        """Stops Minecraft server."""
        r = subprocess.run(["immortalctl", "stop", "mcserver"], check=True)


class VoteCog(BaseCog):
    """Voting Commands."""

    EMOJI = "<:mc:639190697186164756>"

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        self.votes: Dict[str, Vote] = {}

    @commands.group(name="vote")
    async def vote(self, ctx: commands.Context) -> None:
        if not ctx.invoked_subcommand:
            raise CommandError("A subcommand is required!")
    
    @vote.command(name="start", aliases=["boot", "launch"])
    async def start(self, ctx: commands.Context) -> None:
        if not self.votes.get("start"):
            self.votes["start"] = VoteServerStart(threshold=2,
                                                  duration=300.0, 
                                                  bot=self.bot
                                                 )
        await self.votes["start"].add_vote(ctx)
    
    @vote.command(name="stop", aliases=["terminate", "shutdown"])
    async def close(self, ctx: commands.Context) -> None:
        if not self.votes.get("stop"):
            self.votes["stop"] = VoteServerStop(threshold=3, 
                                                duration=300.0, 
                                                bot=self.bot
                                               )
        await self.votes["stop"].add_vote(ctx)

