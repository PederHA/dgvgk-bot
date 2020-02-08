import socket

import discord
from discord.ext import commands
import mcstatus

from cogs.base_cog import BaseCog
from config import MC_SERVER_IP, MC_SERVER_PORT
from utils.converters import IPAddressConverter
from utils.exceptions import CommandError
from utils.serialize import dump_json, load_json

CONF = "DGVGK/minecraft.json"
POI_FILE = "minecraft/poi.json"
HOME_COORDINATES = (-600, 80, 650)


class MinecraftCog(BaseCog):
    """Minecraft Commands."""

    EMOJI = "<:mc:639190697186164756>"
    FILES = [POI_FILE]

    def _get_mc_server(self) -> mcstatus.MinecraftServer:
        return mcstatus.MinecraftServer(MC_SERVER_IP, MC_SERVER_PORT)

    def _get_server_attr(self, attr: str) -> None:  # cba proper type hints rn
        server = self._get_mc_server()
        try:
            attr = getattr(server, attr)
            r = attr()
        except (AttributeError, socket.gaierror, socket.timeout):  # lazy
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
        x, y, z = HOME_COORDINATES
        await ctx.send(f"X: {x} / Y: {y} / Z: {z}")

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

    def _get_poi(self) -> dict:
        return load_json(POI_FILE)

    def _dump_poi(self, poi: dict) -> None:
        dump_json(POI_FILE, poi)

    async def _post_pois(self, ctx: commands.Context, title: str, pois: str) -> None:
        await self.send_embed_message(
            ctx, title=f"{title} (XYZ)", description=pois)


    @commands.group(name="poi")
    async def poi(self, ctx: commands.Context) -> None:
        """Points of Interest."""  
        if not ctx.invoked_subcommand:
            poi = self._get_poi()
            if poi:
                pois = "\n".join(
                    [
                        # Capitalize every word e.g. 'magma lake' -> 'Magma Lake'
                        f"**{' '.join([l.capitalize() for l in location.split(' ')])}**: "
                        f"{x} / {y} / {z}"
                        for location, (x, y, z) in poi.items()
                    ]
                )
                await self.send_embed_message(
                    ctx, title="Points of Interest (XYZ)", description=pois
                )
            else:
                await ctx.send(
                    "No Points of Interests have been added! "
                    f"Try adding one with `{self.bot.command_prefix}poi add`."
                )

    @poi.command(name="get")
    async def poi_get(self, ctx: commands.Context, *location) -> None:
        """Unfinished idk."""
        poi = self._get_poi()
        location = " ".join(location).lower()
        
        if location in poi:
            p = poi[location]
        


    @poi.command(name="add")
    async def poi_add(self, ctx: commands.Context, location: str, x: float, y: float, z: float) -> None:
        poi = self._get_poi()
        poi[location.lower()] = (int(x), int(y), int(z)) # We accept numbers with decimals, 
        self._dump_poi(poi)                              # but cba actually storing floats
        await ctx.send(f"Added **{location}**!")

    @poi.command(name="remove", aliases=["del"])
    async def poi_remove(self, ctx: commands.Context, *location) -> None:
        poi = self._get_poi()
        location = " ".join(location).lower()
        
        if location in poi:
            poi.pop(location)
            self._dump_poi(poi)
            await ctx.send(f"Removed **{location}**.")
        else:
            await ctx.send(f"**{location}** does not exist!")
