import json

from discord.ext import commands

from .access_control import get_trusted_members
from .caching import get_cached
from .json import dump_json_blocking


def get_server_id(ctx: commands.Context, server: str) -> int:
    return ctx.bot.config["servers"][server]


# Blacklist serialization functions
def load_blacklist() -> list:
    return get_cached(BLACKLIST_PATH, "blacklist")


def save_blacklist(blacklist: list) -> None:
    dump_json_blocking(BLACKLIST_PATH, blacklist)


# Decorator check
def admins_only():
    def predicate(ctx):
        if hasattr(ctx.author, "guild_permissions"): # Disables privileged commands in PMs
            return ctx.author.guild_permissions.administrator
        return False
    predicate.doc_prefix = "ADMIN:"
    return commands.check(predicate)


def owners_only():
    """Check if command invoker is in list of owners defined in config.py"""
    def predicate(ctx):
        return ctx.message.author.id == ctx.bot.config["users"]["owner_id"]
    predicate.doc_prefix = "BOT OWNER:"
    return commands.check(predicate)



def guild_predicate(ctx, guild_id):
    if hasattr(ctx.author, "guild"):
        return ctx.message.author.guild.id == guild_id or ctx.message.author.guild.id == get_server_id(ctx, "test")
    return False


def pfm_cmd():
    """PFM guild decorator"""
    def predicate(ctx):
        return guild_predicate(ctx, get_server_id(ctx, "pfm"))
    return commands.check(predicate)


def dgvgk_cmd():
    """DGVGK guild decorator"""
    def predicate(ctx):
        return guild_predicate(ctx, get_server_id(ctx, "dgvgk"))
    return commands.check(predicate)


def test_server_cmd():
    """Test/dev guild decorator"""
    def predicate(ctx):
        return guild_predicate(ctx, get_server_id(ctx, "test"))
    return commands.check(predicate)


def download_cmd():
    """Decorator for download commands"""
    def predicate(ctx):
        return ctx.bot.config["downloads"]["allowed"]
    return commands.check(predicate)


def disabled_cmd():
    """Disables a command for everyone."""
    def predicate(ctx):
        return False
    return commands.check(predicate)


def trusted():
    """Adds check that allows trusted users only."""
    def predicate(ctx):
        if ctx.guild:
            return ctx.message.author.id in get_trusted_members(ctx.guild.id)
        return False
    return commands.check(predicate)
