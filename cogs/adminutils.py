import aiohttp
import json
import discord
import sys
import os
import random
import asyncio
import io, contextlib
from langstr import LangStr
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from playsound3 import playsound
from dotenv import find_dotenv, set_key
OWNER_ID = 1078788946609324175
DEFAULT_USER_DATA = {
    "tickets": 350,
    "tokens": 25,
}
RESTART_TEXT = ['https://tenor.com/view/imbarbarian-gif-10487863430577917562']

class AdminUtils(commands.Cog, name="Admin Utilities"):
    def __init__(self, bot) -> None:
        self.bot = bot  
    
    @commands.hybrid_command(name="restart",
    description="restarts the bot")
    async def restart(self, context: Context):
        if self.bot.get_value(context.author.id, "admin") != True:
            await context.send("you aren't trusted to run that!")
            return
        text = random.choice(RESTART_TEXT)
        await context.send(text)
        os.execv(sys.executable, ['python'] + sys.argv)
        
        
    @commands.hybrid_command(name="shutdown",
    description="shuts-down the bot ")
    async def shutdown(self, context: Context):
        print(context.author.id)
        if self.bot.get_value(context.author.id, "admin") != True:
            await context.send("you aren't trusted to run that!")
            return
        await context.send("WHAAT?! NOOO!! ***DUUUUUDDEEEE!!!!***")
        await self.bot.close()
    
    @commands.hybrid_command(name="kys",
    description="makes the bot kill itself... its the same thing as shutdown tho")
    async def kys(self, context: Context):
        print(context.author.id)
        if self.bot.get_value(context.author.id, "admin") != True:
            await context.send("how about i don't do that >:/")
            return
        await context.send("rude... but yeah okay whatever")
        os._exit(0)
    
    @commands.hybrid_command(name="change_id",
    description="changes the channel where the bot will send/edit leaderboard status.")
    @app_commands.describe(new_id='ID of the channel where the bot will send status')
    async def change_id(self, context: Context, new_id: int):
        if self.bot.get_value(context.author.id, "admin") != True:
            await context.send("you aren't trusted to run that!")
            return
        os.environ["STATUS_CHANNEL_ID"] = str(new_id)
        set_key(find_dotenv(), "STATUS_CHANNEL_ID", os.environ["STATUS_CHANNEL_ID"])
        await context.send(f"done! status should be going to <#{new_id}> now.\nwe're going to restart to apply changes")
        playsound('audio/restart.wav')
        os.execv(sys.executable, ['python'] + sys.argv)
        
    @commands.hybrid_command(
        name="add_stat", 
        description="give a player a stat"
    )
    @app_commands.describe(
        stat='The label of the stat you want to add to', 
        val='The amount you want to add'
    )
    async def add_stat(self, ctx, user: discord.User, stat: str, val: int):
        if self.bot.get_value(ctx.author.id, "admin") != True:
            await context.send("you aren't trusted to run that!")
            return
        new_total = self.bot.add_value(user.id, stat, val)
        await ctx.send(f'{user.display_name} got {val} {stat}.')
    
    @commands.hybrid_command(
        name="get_stat", 
        description="get a player's stat"
    )
    @app_commands.describe(stat='The label of the stat you want to check')
    async def get_stat(self, ctx, user: discord.User, stat: str):
        if self.bot.get_value(ctx.author.id, "admin") != True:
            await context.send("you aren't trusted to run that!")
            return
        value = self.bot.get_value(user.id, stat)
        await ctx.send(f'{user.display_name}\'s {stat} is {value}.')
        
    @commands.hybrid_command(
        name="set_stat", 
        description="set a player's stat"
    )
    @app_commands.describe(
        stat='The label of the stat you want to set', 
        val='The amount you want to set'
    )
    async def set_stat(self, ctx, user: discord.User, stat: str, val: str):
        if self.bot.get_value(ctx.author.id, "admin") != True:
            await context.send("you aren't trusted to run that!")
            return
        if val.isdigit():
            val = int(val)
        if val in ['True', 'False']:
            val = eval(val)
        new_total = self.bot.set_value(user.id, stat, val)
        await ctx.send(f'{user.display_name} had {stat} set to {val}.')
        
    def ensure_user(self, data: dict, user_id: int) -> bool:
        uid = str(user_id)

        if uid not in data:
            data[uid] = DEFAULT_USER_DATA.copy()
            return True  # newly created

        # Fill missing keys only (schema update safety)
        for k, v in DEFAULT_USER_DATA.items():
            data[uid].setdefault(k, v)

        return False
    
    @commands.hybrid_command(name='sync')
    async def sync(self, ctx):
        if self.bot.get_value(ctx.author.id, "admin") != True:
            await ctx.send("you aren't trusted to run that!")
            return
        synced = await ctx.bot.tree.sync()
        print(synced)
        await ctx.send(f"Synced {len(synced)} commands globally.")

    @commands.hybrid_command(
        name="init_members",
        description="Initialize default data for all server members"
    )
    async def init_members(self, ctx):
        if self.bot.get_value(ctx.author.id, "admin") != True:
            await ctx.send("you aren't trusted to run that!")
            return
        guild = ctx.guild
        if not guild:
            return await ctx.send("This command can only be used in a server.")

        data = self.load_data()

        created = 0
        updated = 0

        for member in guild.members:
            if member.bot:
                continue

            if self.ensure_user(data, member.id):
                created += 1
            else:
                updated += 1

        self.save_data(data)

        await ctx.send(
            f"initialization complete!\nmost users should have stats now.\n"
            f"users created: {created}\n"
            f"users updated: {updated}"
        )
            
    @commands.hybrid_command(
        name="execute",
        description="execute a command on the console",
        aliases=['eval'],
    )
    async def execute(self, ctx, cmd: str):
        if self.bot.get_value(ctx.author.id, "admin") is not True:
            await ctx.send("you aren't trusted to run that!")
            return

        buffer = io.StringIO()

        try:
            with contextlib.redirect_stdout(buffer):
                try:
                    result = eval(cmd, globals(), locals())
                except SyntaxError:
                    exec(cmd, globals(), locals())
                    result = None
        except Exception as e:
            await ctx.send(f"error:\n```py\n{type(e).__name__}: {e}```")
            return

        output = buffer.getvalue().strip()

        if output and result is not None:
            await ctx.send(f"output:\n```py\n{output}```\nresult: ```py\n{repr(result)}```")
        elif output:
            await ctx.send(f"output:\n```py\n{output}```")
        else:
            await ctx.send(f"result:\n```py\n{repr(result)}```")
        
async def setup(bot) -> None:
    await bot.add_cog(AdminUtils(bot))