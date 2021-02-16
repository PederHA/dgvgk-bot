"""
Not technically cog, but who's gonna fucking arrest me, huh?
"""
from __future__ import annotations

import asyncio
import random
import sqlite3
from typing import Tuple, List, Dict, Callable, Any, Iterable, Optional
from dataclasses import dataclass

import discord
from discord.ext import commands

from ..utils.exceptions import CommandError


_COORD_TYPE = Tuple[str, str, float, float, float]
@dataclass
class Coordinates:
    name: str
    description: Optional[str]
    x: float
    y: float
    z: float

    @classmethod
    def _from_db(cls, result: _COORD_TYPE) -> Coordinates:
        return cls(
            name=result[0],
            description=result[1],
            x=result[2],
            y=result[3],
            z=result[4],
        )



class DatabaseConnection:
    def __init__(self, db_path: str, bot: commands.Bot) -> None:
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor: sqlite3.Cursor = self.conn.cursor()
        self.bot = bot # To run blocking methods in thread pool
        
        # I was planning to add separate read and write locks,
        # but I'm not actually sure if that's safe. 
        # So for now, both read and write locks share the same lock.
        self.rlock = asyncio.Lock()
        self.wlock = self.rlock
        
    async def read(self, meth: Callable[..., Any], *args) -> Any:
        async with self.rlock:
            return await self.bot.loop.run_in_executor(None, meth, *args)

    async def write(self, meth: Callable[..., Any], *args) -> Any:
        async with self.wlock:
            def to_run():
                r = meth(*args)
                self.conn.commit()
                return r
            return await self.bot.loop.run_in_executor(None, to_run)

    async def get_last_ip(self) -> Optional[str]:
        ip = await self.read(self._get_last_ip)
        try:
            return ip[0]
        except (IndexError, TypeError):
            return None

    def _get_last_ip(self) -> Tuple[str]:
        self.cursor.execute("SELECT ip from ip LIMIT 1")
        return self.cursor.fetchone()

    async def save_last_ip(self, ip: str) -> None:
        return await self.write(self._save_last_ip, ip)

    def _save_last_ip(self, ip: str) -> None:
        # Single row table, always overwrite row with id 1
        self.cursor.execute("""
            INSERT INTO `ip` (id, ip)
            SET ip = ?
            WHERE id == 1
            """
        )
        
    async def get_home_coordinates(self) -> Coordinates:
        r = await self.read(self._get_home_coordinates)
        if not r:
            raise ValueError("No POI for 'home' found.")
        return Coordinates._from_db(r)
        

    def _get_home_coordinates(self) -> Tuple[str, str, float, float, float]:
        self.conn.execute("""
            SELECT *
            FROM `poi`
            WHERE name==?
            """, ("home")
        )
        return self.cursor.fetchone()