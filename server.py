import asyncio
import glob
import os
from datetime import datetime

from discord.ext import tasks, commands
from discord.ext.commands import has_permissions
from file_read_backwards import FileReadBackwards
from rcon.source import Client


class ServerHandler(commands.Cog):
    """
    Class which handles printing log files to the main zomboid channel
    """

    def __init__(self, bot, logPath):
        self.bot = bot
        self.logPath = logPath
        self.lastUpdateTimestamp = datetime.now()
        self.update.start()
        self.webhook = None

    def splitLine(self, line: str):
        """Split a log line into a timestamp and the remaining message"""
        timestampStr, message = line.strip()[1:].split("]", 1)
        timestamp = datetime.strptime(timestampStr, "%d-%m-%y %H:%M:%S.%f")
        return timestamp, message

    @commands.command()
    @has_permissions(administrator=True)
    async def manual_restart(self, ctx):
        if not self.restart_server.is_running():
            self.restart_server.start()
            await ctx.send("Manually restarting server.")
        else:
            await ctx.send("Already restarting")

    @tasks.loop(hours=24)
    async def restart_server(self):
        """Restart the Project Zomboid server every 24 hours."""

        async def send_server_message(self, message: str):
            """Send a message to the server."""
            with Client(
                self.rconHost,
                self.rconPort,
                passwd=self.rconPassword,
                timeout=5.0,
            ) as client:
                client.run(f'/servermsg "{message}"')

        # Send restart message in Discord once
        await self.bot.channel.send("Server will restart in 5 minutes.")

        # Send many warning messages in-game
        countdown_intervals = [
            (300, "Server will restart in 5 minutes."),
            (60, "Server will restart in 1 minute."),
            (30, "Server will restart in 30 seconds."),
            (20, "Server will restart in 20 seconds."),
            (10, "Server will restart in 10 seconds."),
            (9, "Server will restart in 9 seconds."),
            (8, "Server will restart in 8 seconds."),
            (7, "Server will restart in 7 seconds."),
            (6, "Server will restart in 6 seconds."),
            (5, "Server will restart in 5 seconds."),
            (4, "Server will restart in 4 seconds."),
            (3, "Server will restart in 3 seconds."),
            (2, "Server will restart in 2 seconds."),
            (1, "Server will restart in 1 second."),
        ]

        for seconds, message in countdown_intervals:
            await self.send_server_message(message)
            await asyncio.sleep(seconds)

        # Send messge to Discord and server when restarting
        restarting_message = "Restarting server now."
        await self.bot.channel.send(restarting_message)
        await self.send_server_message(restarting_message)

        # Restart the server using the shell script
        SERVER_START_COMMAND = os.getenv("START_SERVER_COMMAND")
        os.system(f"./restart_pz_server.sh '{SERVER_START_COMMAND}'")

    @tasks.loop(seconds=10)
    async def update(self):
        # Don't really know how performant this will be since it's opening 4
        # files -- set it to 10 seconds loop for now
        debug_server_file_type = "DebugLog-server.txt"
        files = glob.glob(f"{self.logPath}/*{debug_server_file_type}")
        files = [
            file for sublist in files for file in sublist
        ]  # Flatten the list of lists
        if len(files) > 0:
            for file in files:
                with FileReadBackwards(file) as f:
                    for line in f:
                        timestamp, message = self.splitLine(line)
                        await self.handleDebugLog(timestamp, message)

    async def handleLog(self, timestamp: datetime, message: str):
        """Parse the DebugLog-server.txt logfile and act on certain triggers."""

        # Check for the server start message
        if "SERVER STARTED" in message:
            # Handle server start here. For instance:
            if self.adminChannel:
                await self.adminChannel.send("Server has started!")
            return

        # Check for the server end message
        if "Trying to close low level socket support" in message:
            # Handle server end here. For instance:
            if self.adminChannel:
                await self.adminChannel.send("Server is shutting down!")
            return
