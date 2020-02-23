import asyncio
import inspect
import subprocess
from abc import ABCMeta, abstractmethod
from datetime import datetime
from typing import Dict

import discord
from discord.ext import commands

from cogs.base_cog import BaseCog
from utils.exceptions import CommandError


class Vote:
    """Sort of unused atm."""
    def __init__(self, ctx: commands.Context) -> None:
        self.voter: discord.Member = ctx.message.author
        self.time: datetime = ctx.message.created_at


class VotingSession(metaclass=ABCMeta):
    """Represents a voting session."""

    def __init__(self,
                 ctx: commands.Context,
                 threshold: int, 
                 duration: float,
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
        self.threshold = threshold
        self.duration = duration
        self.bot: commands.Bot = ctx.bot
        self.ctx: commands.Context = ctx
        self.loop: asyncio.Task = None
        self.reset() 
        # TODO: Add superuser vote weighting
        #       Add superuser supervote (triggers action)
    
    def reset(self) -> None:
        """Resets voting session."""
        self.start = datetime.now()
        self.votes: Dict[int, Vote] = {}
        if self.loop:
            self.bot.loop.create_task(self.stop_loop())

    @property
    def remaining(self) -> int:
        return self.threshold - len(self.votes)

    @property
    def current(self) -> int:
        return len(self.votes)

    @property
    def elapsed(self) -> float:
        return (datetime.now() - self.start).total_seconds()

    async def start_loop(self) -> None:
        self.loop = self.bot.loop.create_task(self.sessionloop())

    async def stop_loop(self) -> None:
        if not self.loop:
            raise AttributeError("No session loop is active.")
        self.loop.cancel()

    async def sessionloop(self, interval: int=10) -> None:
        """Periodically checks if voting session is still active."""
        while True:
            if self.elapsed > self.duration:
                await self.ctx.send("Voting session ended. Not enough votes.")
                self.reset()
            await asyncio.sleep(interval)

    async def check_votes(self) -> bool:
        """Checks if sufficient votes are reached."""
        return len(self.votes) >= self.threshold    
    
    async def add_vote(self, ctx: commands.Context) -> None:
        """Adds a vote. Performs action if enough votes are cast."""
        # Add vote
        if self.elapsed < self.duration: # Check if voting session is active
            if not await self._vote_exists(ctx):
                await self._add_vote(ctx)
            else:
                return # this is a little messy
        else:
            self.reset() # reset voting session
            await self._add_vote(ctx)

        # Start voting session loop
        if not self.loop:
            await self.start_loop()

        # Run action if enough votes
        if await self.check_votes():
            await ctx.send(f"Sufficient votes received!") # NOTE: remove?
            await self._do_action(ctx)
        else:
            s = "s are" if self.remaining > 1 else " is"
            await ctx.send(f"Vote added! {self.remaining} more vote{s} required.")

    async def _add_vote(self, ctx: commands.Context) -> None:
        self.votes[ctx.message.author.id] = Vote(ctx)

    async def _do_action(self, ctx: commands.Context) -> None:
        """Tries to perform action. Runs cleanup if action fails."""
        try:
            await self.action_start(ctx)
        except:
            await self.action_failed(ctx)
            raise # Raise original exception so exception handler can catch it
        else:
            await self.action_finished(ctx)

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

    @abstractmethod
    async def action_start(self, ctx) -> None:
        """Performs action. Subclasses need to define this method."""
        ...

    @abstractmethod
    async def action_finished(self, ctx: commands.Context) -> None:
        """Defines what to do when action has successfully completed."""
        ...

    @abstractmethod
    async def action_failed(self, ctx: commands.Context) -> None:
        """Defines behavior when action fails. Cleanup etc. should be performed here."""
        ...

    async def action_cancel(self, ctx: commands.Context) -> None:
        """Optional method to cancel action. (Canceling NYI.) """
        raise NotImplementedError


class VoteServerStart(VotingSession):
    async def action_start(self, ctx: commands.Context) -> None:
        """Starts Minecraft server."""
        await ctx.send("Sufficient votes received! Starting Minecraft server...")
        # self.msg = msg
        # delete message afterwards... 
        subprocess.run(["immortalctl", "start", "mcserver"], check=True) 
        # param check raises exception if non-0 exit code

    async def action_finished(self, ctx: commands.Context) -> None:
        await ctx.send("Started Minecraft server!")
    
    async def action_failed(self, ctx: commands.Context) -> None:
        await ctx.send("Failed to start server.")


class VoteServerStop(VotingSession):
    async def action_start(self, ctx: commands.Context) -> None:
        """Stops Minecraft server."""
        await ctx.send("Stopping Minecraft server...")
        subprocess.run(["immortalctl", "stop", "mcserver"], check=True)

    async def action_finished(self, ctx: commands.Context) -> None:
        await ctx.send("Minecraft server stopped.")

    async def action_failed(self, ctx: commands.Context) -> None:
        await ctx.send("Failed to stop server. Is the server already down?")
        # cleanup?


class VoteCog(BaseCog):
    """Voting Commands."""

    EMOJI = ":put_litter_in_its_place:"

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        self.votes: Dict[str, VotingSession] = {}

    @commands.group(name="vote")
    async def vote(self, ctx: commands.Context) -> None:
        if not ctx.invoked_subcommand:
            raise CommandError("A subcommand is required!")
    
    @vote.command(name="start", aliases=["boot", "launch"])
    async def start(self, ctx: commands.Context) -> None:
        """Vote to start the MC server."""
        if not self.votes.get("start"):
            self.votes["start"] = VoteServerStart(ctx,
                                                  threshold=2,
                                                  duration=300.0)
        await self.votes["start"].add_vote(ctx)
    
    @vote.command(name="stop", aliases=["terminate", "shutdown"])
    async def stop(self, ctx: commands.Context) -> None:
        """Vote to stop the MC server."""
        if not self.votes.get("stop"):
            self.votes["stop"] = VoteServerStop(ctx,
                                                threshold=3, 
                                                duration=300.0)
        await self.votes["stop"].add_vote(ctx)
