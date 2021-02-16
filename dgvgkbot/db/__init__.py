from typing import Dict
from pathlib import Path

from discord.ext import commands

from .db import DatabaseConnection

# Maybe this is a little clumsy?
_CONNECTIONS: Dict[str, DatabaseConnection] = {}


def add_db(path: Path, bot: commands.Bot) -> DatabaseConnection:
    if path not in _CONNECTIONS:
        _CONNECTIONS[path] = DatabaseConnection(path, bot)
    return _CONNECTIONS[path]


def get_db(path: str) -> DatabaseConnection:
    return _CONNECTIONS[path]


def init_db(bot: commands.Bot):
    p = Path(bot.config["paths"]["db"])
    
    # Create db if it doesn't exist
    if not p.exists():
        # NOTE: assumes the database file resides in a subdirectory 
        #       within the project root
        #
        # TODO: Actually make this not completely explode if the db file resides in
        #       the root directory.
        p.parent.mkdir(parents=True, exist_ok=True)
        p.touch()

    # Connect to DB
    db = add_db(p, bot)

    # Add tables (if not already exists)
    with open("db/dgvgkbot.sql", "r") as f:
        script = f.read()
    db.cursor.executescript(script)

    return db
