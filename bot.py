"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized Discord bot in Python

Version: 6.4.0
"""

import json
import logging
import os
import platform
import random
import sys
import time
import aiohttp
import math
import asyncio
import langstr

import aiosqlite
import discord
from discord.ext import commands, tasks
from discord.ext.commands import Context
from discord import app_commands
from dotenv import load_dotenv, find_dotenv
from playsound3 import playsound

from database import DatabaseManager # type: ignore

load_dotenv()

"""	
Setup bot intents (events restrictions)
For more information about intents, please go to the following websites:
https://discordpy.readthedocs.io/en/latest/intents.html
https://discordpy.readthedocs.io/en/latest/intents.html#privileged-intents


Default Intents:
intents.bans = True
intents.dm_messages = True
intents.dm_reactions = True
intents.dm_typing = True
intents.guild_scheduled_events = True
intents.integrations = True
intents.invites = True
# `message_content` is required to get the content of the messages
intents.reactions = True
intents.voice_states = True


Privileged Intents (Needs to be enabled on developer portal of Discord), please use them only if you need them:
"""

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True
intents.guild_messages = True
intents.emojis = True
intents.emojis_and_stickers = True
intents.guild_reactions = True
intents.guild_typing = True
intents.messages = True 
intents.webhooks = True
intents.typing = True
SERVER_URL = "https://bombsquda.tailc76b25.ts.net/"
STATUS_CHANNEL_ID = int(os.getenv('STATUS_CHANNEL_ID'))
STATUS_MESSAGE_ID = None
STATUS_FILE = "status_message.json"
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

"""
Uncomment this if you want to use prefix (normal) commands.
It is recommended to use slash commands and therefore not use prefix commands.

If you want to use prefix commands, make sure to also enable the intent below in the Discord developer portal.
"""
# intents.message_content = True

# Setup both of the loggers


class LoggingFormatter(logging.Formatter):
    # Colors
    black = "\x1b[30m"
    red = "\x1b[31m"
    green = "\x1b[32m"
    yellow = "\x1b[33m"
    blue = "\x1b[34m"
    gray = "\x1b[38m"
    # Styles
    reset = "\x1b[0m"
    bold = "\x1b[1m"

    COLORS = {
        logging.DEBUG: gray + bold,
        logging.INFO: blue + bold,
        logging.WARNING: yellow + bold,
        logging.ERROR: red,
        logging.CRITICAL: red + bold,
    }

    def format(self, record):
        log_color = self.COLORS[record.levelno]
        format = "(black){asctime}(reset) (levelcolor){levelname:<8}(reset) (green){name}(reset) {message}"
        format = format.replace("(black)", self.black + self.bold)
        format = format.replace("(reset)", self.reset)
        format = format.replace("(levelcolor)", log_color)
        format = format.replace("(green)", self.green + self.bold)
        formatter = logging.Formatter(format, "%Y-%m-%d %H:%M:%S", style="{")
        return formatter.format(record)


logger = logging.getLogger("discord_bot")
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(LoggingFormatter())
# File handler
file_handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
file_handler_formatter = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name}: {message}", "%Y-%m-%d %H:%M:%S", style="{"
)
file_handler.setFormatter(file_handler_formatter)

# Add the handlers
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# the bot!!!
class SpazBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned_or(os.getenv("PREFIX"), os.getenv("PREFIX2")),
            intents=intents,
            help_command=None,
        )
        self.logger = logger
        self.database = None
        self.bot_prefix = os.getenv("PREFIX")
        self.invite_link = os.getenv("INVITE_LINK")
        lang_path = os.path.realpath(os.path.dirname(__file__)) + '/lang'
        langstr.set_path(lang_path)

    async def init_db(self) -> None:
        async with aiosqlite.connect(
            f"{os.path.realpath(os.path.dirname(__file__))}/database/database.db"
        ) as db:
            with open(
                f"{os.path.realpath(os.path.dirname(__file__))}/database/schema.sql",
                encoding = "utf-8"
            ) as file:
                await db.executescript(file.read())
            await db.commit()
            
    def save_status_message_id(self, message_id: int):
        with open(STATUS_FILE, "w") as f:
            json.dump({"message_id": message_id}, f)

    def load_status_message_id(self):
        if not os.path.exists(STATUS_FILE):
            return None
        with open(STATUS_FILE, "r") as f:
            return json.load(f).get("message_id")
            
    async def get_or_create_status_message(self, channel: discord.TextChannel):
        msg_id = self.load_status_message_id()

        if msg_id:
            try:
                return await channel.fetch_message(msg_id)
            except:
                pass  # message was deleted

        embed = discord.Embed(title="BombSquda Leaderboard", description="Starting...", color=0x95a5a6)
        msg = await channel.send(embed=embed)

        self.save_status_message_id(msg.id)
        return msg
        
    @tasks.loop(seconds=15)
    async def check_server(self):
        channel = self.get_channel(STATUS_CHANNEL_ID)
        if not channel:
            return

        msg = await self.get_or_create_status_message(channel)

        online = False
        try:
            start = time.perf_counter()
            async with aiohttp.ClientSession() as session:
                async with session.get(SERVER_URL, timeout=5):
                    online = True
        except Exception as e:
            online = False

        color = 0x2ecc71 if online else 0xe74c3c
        status = (
            f"online at {SERVER_URL} !" 
            if online else 
            "offline. spazbot is either off, the server is, or it's broken. please wait!"
        )
        desc = f"{status}\n"

        embed = discord.Embed(title="BombSquda Leaderboard Status", description=desc, color=color)

        await msg.edit(embed=embed)


    async def load_cogs(self) -> None:
        """
        The code in this function is executed whenever the bot will start.
        """
        for file in os.listdir(f"{os.path.realpath(os.path.dirname(__file__))}/cogs"):
            if file.endswith(".py"):
                extension = file[:-3]
                try:
                    await self.load_extension(f"cogs.{extension}")
                    self.logger.info(f"Loaded extension '{extension}'")
                except Exception as e:
                    exception = f"{type(e).__name__}: {e}"
                    self.logger.error(
                        f"Failed to load extension {extension}\n{exception}"
                    )

    @tasks.loop(seconds=20)
    async def status_task(self) -> None:
        """
        Setup the game status task of the bot.
        """
        statuses = [
            'killing meliso', 
            'wasting resources',
            'being goofy',
            'looking towards nothing',
            'doin a bombjump',
            'making commits',
            'killing other spazzes',
            'Teleporting bread...',
            'gaining conscience...',
            'TypeError: status is not defined',
            'Beep boo bo bap bu bu bap.',
            'Hey look, I\'m alive!',
            'looking at your profile',
            'spaz botting',
            'scanning your face (for chat)',
            'Playing BombSquad: Gardenful Modpack',
            'Playing BombSquad',
            'Playing BombSquad: Joyride Modpack',
            'Playing BombSquda',
            'try running \'spazbot, grind\'!',
            'being evil (i guess)',
        ]
        await self.change_presence(activity=discord.Game(random.choice(statuses)))
        
    @status_task.before_loop
    async def before_status_task(self) -> None:
        """
        Before starting the status changing task, we make sure the bot is ready
        """
        await self.wait_until_ready()
        

    async def setup_hook(self) -> None:
        """
        This will just be executed when the bot starts the first time.
        """
        self.logger.info(f"Logged in as {self.user.name}")
        self.logger.info(f"discord.py API version: {discord.__version__}")
        self.logger.info(f"Python version: {platform.python_version()}")
        self.logger.info(
            f"Running on: {platform.system()} {platform.release()} ({os.name})"
        )
        self.logger.info("-------------------")
        await self.init_db()
        await self.load_cogs()
        # Clean expired rob multipliers on startup
        fun_cog = self.get_cog("Fun")
        if fun_cog:
            fun_cog.clean_expired_rob_multi()
        self.status_task.start()
        self.check_server.start()
        self.database = DatabaseManager(
            connection=await aiosqlite.connect(
                f"{os.path.realpath(os.path.dirname(__file__))}/database/database.db"
            )
        )

    async def on_command_completion(self, context: Context) -> None:
        """
        The code in this event is executed every time a normal command has been *successfully* executed.

        :param context: The context of the command that has been executed.
        """
        full_command_name = context.command.qualified_name
        split = full_command_name.split(" ")
        executed_command = str(split[0])
        if context.guild is not None:
            self.logger.info(
                f"Executed {executed_command} command in {context.guild.name} (ID: {context.guild.id}) by {context.author} (ID: {context.author.id})"
            )
        else:
            self.logger.info(
                f"Executed {executed_command} command by {context.author} (ID: {context.author.id}) in DMs"
            )
    
    async def on_message(self, message):
        await self.process_commands(message)
        
bot = SpazBot()
# ------------------------ bot events ------------------------------------------
def truncate_float(n, decimals=0):
    multiplier = 10**decimals
    return math.trunc(n * multiplier) / multiplier

@bot.event
async def on_command_error(ctx, error):
    
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"you didn't supply the argument {error.param.name}. try again with it.")
        ctx.command.reset_cooldown(ctx)
        
    elif isinstance(error, commands.CommandNotFound):
        await ctx.reply(
            (
                f"{error}! try sending 'spazbot, help' for all commands\nREMINDER: my "
                'prefix is either "sb!command", "spazbot, command", '
                '@SpazBot command", or just plain slash commands.'
            )
        )
        
    elif isinstance(error, commands.UserNotFound):
        await ctx.reply(
            (
                f"we couldn't find user {error.argument}. you should a supply a "
                "user by their @Mention, user_name, or Display Name."
            )
        )
        ctx.command.reset_cooldown(ctx)
        
    elif isinstance(error, commands.MemberNotFound):
        await ctx.reply(
            (
                f"we couldn't find member {error.argument}. you should a supply a user by their "
                "@Mention, user_name, or Display Name.\nREMINDER: users from other servers "
                "can't be used for these types of commands."
            )
        )
        ctx.command.reset_cooldown(ctx)
        
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.reply(f'command is on cooldown, try again after {truncate_float(error.retry_after, 1)}s <a:thumbsdown:1462932503001039014>')
        
    elif isinstance(error, asyncio.TimeoutError):
        await ctx.reply('you took too long, and the command timed out. try again.')
        
    elif isinstance(error, aiohttp.ClientConnectorError):
        await ctx.reply('connection failed! the requested server is either down or non functioning.')
        
        path = f'{__file__}\\audio\\error.wav'.replace('\\', '/') 
        path = path.replace('bot.py/', '') 
        playsound(path, block=False)
        
    elif isinstance(error, discord.ext.commands.errors.BadArgument):
        await ctx.reply(f'a bad argument was given.\n`{error}`')
        
    else:
        await ctx.reply(f'unhandled error occured:\n`{error}`\nif you can, report it or make a issue on the github (if it\'s likely a issue)')
        ctx.command.reset_cooldown(ctx)
        
        path = f'{__file__}\\audio\\error.wav'.replace('\\', '/') 
        path = path.replace('bot.py/', '') 
        playsound(path, block=False)
        raise error # raise so we know what it is
    
# ------------------------ bot events ------------------------------------------  
path = f'{__file__}\\audio\\start.wav'.replace('\\', '/') 
path = path.replace('bot.py/', '') 
playsound(path, block=False)
bot.run(os.getenv("TOKEN"))

