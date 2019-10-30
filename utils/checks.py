import json

from discord.ext import commands
from config import (DGVGK_SERVER_ID, DOWNLOADS_ALLOWED, OWNER_ID,
                    PFM_SERVER_ID, TEST_SERVER_ID, BLACKLIST_PATH)
from utils.caching import get_cached
from utils.serialize import dump_json
from utils.access_control import get_trusted_members


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
        return ctx.message.author.id == OWNER_ID
    predicate.doc_prefix = "BOT OWNER:"
    return commands.check(predicate)