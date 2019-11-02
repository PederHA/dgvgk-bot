import socket

import discord
from discord.ext import commands
import mcstatus

from cogs.base_cog import BaseCog
from config import MC_SERVER_IP, MC_SERVER_PORT
from utils.converters import IPAddressConverter
from utils.exceptions import CommandError
from utils.serialize import dump_json
from utils.caching import get_cached

CONF = "DGVGK/minecraft.json"

class MinecraftCog(BaseCog):
    """Minecraft Commands."""

    EMOJI = "<:mc:639190697186164756>"
    HOME_COORDS = (-600, 80, 650)

    def _get_mc_server(self) -> mcstatus.MinecraftServer:
        return mcstatus.MinecraftServer(MC_SERVER_IP, MC_SERVER_PORT)
    
    def _get_server_attr(self, attr: str) -> None: # cba proper type hints rn
        server = self._get_mc_server()
        try:
            attr = getattr(server, attr)
            r = attr()
        except (AttributeError, socket.gaierror, socket.timeout): # lazy
            raise CommandError("Unable to connect to server")
        else:
            return r
    
    async def get_server_status(self) -> mcstatus.pinger.PingResponse:
        return self._get_server_attr("status")

    async def query_server(self) -> mcstatus.querier.QueryResponse:
        return self._get_server_attr("query")

    @commands.group(name="mc")
    async def mc(self, ctx: commands.Context) -> None:
        if not ctx.invoked_subcommand:
            cmd = self.bot.get_command("help")
            await ctx.invoke(cmd, "mc")

    @mc.command(name="players")
    async def view_players(self, ctx: commands.Context) -> None:
        """Online players on the server."""
        status = await self.get_server_status()
        players = status.players.sample
       
        # Since mcstatus is a piece of trash, we have to do this
        if not players:
            return await ctx.send("No players are currently online")
        
        msg_body = "\n".join([player.name for player in players])
        await self.send_embed_message(ctx, title="Players Online", description=msg_body)

    @mc.command(name="plugins")
    async def query(self, ctx: commands.Context) -> None:
        """Active plugins on the server."""
        query = await self.query_server()
        plugins = query.software.plugins
        
        if not plugins:
            return await ctx.send("Server has no active plugins.")
        
        msg_body = "\n".join([plugin for plugin in plugins])
        await self.send_embed_message(ctx, title="Active Plugins", description=msg_body)
    
    @mc.command(name="home", aliases=["base"])
    async def home_coordinates(self, ctx: commands.Context) -> None:
        """Coordinates of home base."""
        c = self.HOME_COORDS
        await ctx.send(f"X: {c[0]} / Y: {c[1]} / Z: {c[2]}")
    
    async def server_status_str(self) -> str:
        """Unused rn. Pending removal tbqh"""
        try:
            await self.get_server_status()
        except CommandError:
            online = False
        else:
            online = True

        status = "ONLINE ✅" if online else "OFFLINE ❌"
        
        return f"Minecraft: {status}"

    async def n_players_online(self) -> str:
        try:
            status = await self.get_server_status()
        except CommandError:
            return "Server Offline ❌"
        else:
            return f"Players: {status.players.online}"