"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized Discord bot in Python

Version: 6.4.0
"""

import platform
import random

import json
import aiohttp
import discord
import requests
import sys
import os
import langstr
from mss import mss
from pathlib import Path
import mss
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from playsound3 import playsound

GREETINGS = [
    "greetings!",
    "here i am!",
    "howdy.",
    "name's spazbot!",
    "i'm up and runnin'!",
]

class HelpView(discord.ui.View):
    def __init__(self, *, bot: commands.Bot, author: discord.Member, pages: list[discord.Embed]):
        super().__init__(timeout=120)

        self.bot = bot
        self.author = author
        self.pages = pages
        self.index = 0

        self._update_buttons()

    def _update_buttons(self):
        self.prev_button.disabled = self.index <= 0
        self.next_button.disabled = self.index >= len(self.pages) - 1

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message(
                "this ain't your help menu.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(emoji="<a:arrow_left:1463262102545236170>", style=discord.ButtonStyle.grey)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index -= 1
        self._update_buttons()
        await interaction.response.edit_message(
            embed=self.pages[self.index],
            view=self
        )

    @discord.ui.button(emoji="<a:arrow_right:1463262135806328965>", style=discord.ButtonStyle.grey)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index += 1
        self._update_buttons()
        await interaction.response.edit_message(
            embed=self.pages[self.index],
            view=self
        )

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

class General(commands.Cog, name="General"):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        name="help",
        description="shows all commands that you can use"
    )
    @commands.cooldown(1, 20, commands.BucketType.user)
    async def help(self, context: Context):

        pages: list[discord.Embed] = []

        for cog_name in self.bot.cogs:
            # owner-only cog check
            if cog_name.lower() == "owner":
                if not await self.bot.is_owner(context.author):
                    continue

            cog = self.bot.get_cog(cog_name)
            if not cog:
                continue

            cmds = cog.get_commands()
            if not cmds:
                continue

            lines = []
            for command in cmds:
                desc = command.description.partition("\n")[0]
                lines.append(f"{command.name} — {desc}")

            embed = discord.Embed(
                title=f"{cog_name} Commands",
                description="here's what you can use (try not to screw it up).",
                color=0xBEBEFE
            )

            embed.add_field(
                name="",
                value=f"```{chr(10).join(lines)}```",
                inline=False
            )

            embed.set_footer(text="(use the buttons to switch pages)")

            pages.append(embed)

        if not pages:
            await context.send("no commands found.")
            return

        view = HelpView(
            bot=self.bot,
            author=context.author,
            pages=pages
        )

        await context.send(
            embed=pages[0],
            view=view
        )

    @commands.hybrid_command(
        name="say", 
        description=(
            "make me say something!"
            " REMINDER: use double quotes for messages with spaces"
        )   
    )
    @commands.cooldown(1, 1, commands.BucketType.user)
    async def say(self, ctx, message: str):
        if '@' in message:
            await ctx.send("pings aren't allowed in say!")
            return
        await ctx.send(message)
        
    @commands.hybrid_command(
        name="ping",
        description="check if the bot is alive and well!",
    )
    async def ping(self, context: Context) -> None:
        lat = round(self.bot.latency * 1000)
        await context.send(f'pong! latency is {lat}ms')

    # FIXME: no point in using this if ping alr exists
    @commands.hybrid_command(
        name="hello",
        description=(
            "reply with hello! used for testing "
            "if the bot is working or not"
        )
    )
    async def hello(self, context: Context):
        await context.send(random.choice(GREETINGS))

    # placeholder for possible future ai features
    # ...maybe
    @commands.hybrid_command(
        name="ai",
        description='Use the ultimate generative AI to generate the BEST answers for your questions!'
    )
    async def ai(self, context: Context, question: str):
        answers = [
            'i dunno.',
            'yeah like maybe',
            'totally!',
            'nope.',
            'hell no!',
            'can\'t answer that.',
            'ask something else....',
            'maybe you\'ll find out.',
            'hmmmm... maybe not.',
            'maybe, yeah...',
        ]
        await context.send(f'-# {context.author.display_name} asked: `{question}`\n{random.choice(answers)}')
    
    # Thanks to buddiew for this peak code 
    # :sunglasses_moment:
    @commands.hybrid_command(
        name="screenshot", 
        description="take a screenshot of mell's screen (so you know what he's doin)")
    @commands.cooldown(1, 5, commands.BucketType.user) 
    async def scren(self, ctx: Context):
        # python allows for defs inside defs, so just put it here
        def on_exists(fname: str) -> None:
            file = Path(fname)
            if file.is_file():
                file.unlink()
        # run it ONCE the command is called
        with mss.mss() as sct:
            filename = sct.shot(output="LatestScreenshot.png", callback=on_exists)
            print("Took a screenshot at:")
            print(f'{ctx.channel.name}, at server {ctx.guild.name}')
            dir = Path(__file__).resolve().parent.parent
            spath = dir / 'audio/notif.wav'
            playsound(spath, block=False)
        await ctx.defer()
        await ctx.reply(file=discord.File(f'{filename}'))
    
    @commands.hybrid_command(
        name="language",
        description="sets your language!!",
        aliases=['lang'],
    )
    async def set_lang(self, ctx: Context, lang: str):
        if lang not in langstr.get_languages():
            await ctx.reply(
                langstr.LangStr(r='unknownLanguage',
                    s=[
                        ('${LANG}', lang),
                        ('${LIST}', langstr.get_languages()),
                    ],
                    l='english',
                )
            )
            return
        self.bot.set_value(ctx.author.id, 'language', lang)
        await ctx.reply(
            langstr.LangStr(r='languageSet',
                s=[('${LANG}', lang)],
                l=lang,
            )
        )

async def setup(bot) -> None:
    await bot.add_cog(General(bot))
