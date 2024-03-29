"""
Add/remove bot cogs in this module.
"""

from discord.ext import commands

from .admin_cog import AdminCog
from .mc_cog import MinecraftCog
from .stats_cog import StatsCog
from .user_cog import UserCog
from .vote_cog import VoteCog


# List of all cogs in the local namespace
# This should be imported in the bot's main module
COGS = [
    v for k, v in dict(locals()).items()
    if k.endswith("Cog") and issubclass(v, commands.Cog)
]
