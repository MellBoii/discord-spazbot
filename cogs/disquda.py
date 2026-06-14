import asyncio
import json
import os
import math
import platform
import random
import aiohttp
import discord
import typing
import requests
import urllib
import re
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
URL = "http://104.196.199.18:5000/"

class LeaderboardView(discord.ui.View):
    def __init__(self, ctx, data, format_time, pretty_name,
                 difficulty="all", sort_mode="best"):
        super().__init__(timeout=120)

        self.ctx = ctx
        self.data = data
        self.format_time = format_time
        self.pretty_name = pretty_name

        self.difficulty = difficulty
        self.sort_mode = sort_mode
        self.player_count = 0

        self.levels = self.filter_levels()
        self.page = 0
        self.per_page = 3
        self.max_page = max(0, math.ceil(len(self.levels) / self.per_page) - 1)
        self.add_item(DifficultySelect(self.difficulty))
        self.add_item(PlayerCountSelect(self.player_count))

    def filter_levels(self):
        levels = []

        categories = (
            self.data.items()
            if self.difficulty == "all"
            else [(self.difficulty.title(), self.data.get(self.difficulty.title(), {}))]
        )

        for category, category_levels in categories:
            for level_name, level_data in category_levels.items():
                level_name = self.pretty_name(level_name)
                if self.player_count:
                    has_matching_count = any(
                        int(re.match(r"(\d+)", key).group(1))
                        and int(
                            re.match(r"(\d+)", key).group(1)
                        ) == int(self.player_count)
                        for key in level_data
                        if key != "score_type"
                    )

                    if not has_matching_count:
                        continue

                levels.append(
                    (category, level_name, level_data)
                )

        return levels

    # ----------------------------
    # Embed builder
    # ----------------------------

    def build_embed(self):
        embed = discord.Embed(
            title="BombSquda Co-op Leaderboard",
            color=0x41ab4d
        )

        start = self.page * self.per_page
        end = start + self.per_page
        page_levels = self.levels[start:end]

        for category, level_name, level_data in page_levels:
            score_type = level_data.get("score_type", "points")

            lines = []

            for key, scores in level_data.items():
                if key == "score_type":
                    continue
                
                import re
                match = re.match(r"(\d+)", key)
                player_count = int(match.group(1))
                lines.append(f'{player_count} Players')
                
                for i, (score, player) in enumerate(scores, start=1):
                    lines.append(
                        f"**{i}. {player}** — `{score}`"
                    )

                lines.append("")

            embed.add_field(
                name=f"{category}: {level_name}",
                value="\n".join(lines),
                inline=False
            )
        
        return embed
                
    @discord.ui.button(emoji="<a:darrow_left_big:1474535619798499352>", style=discord.ButtonStyle.gray)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = 0
        await interaction.response.edit_message(
            embed=self.build_embed(), view=self
        )

    @discord.ui.button(emoji="<a:arrow_left:1463262102545236170>", style=discord.ButtonStyle.gray)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        await interaction.response.edit_message(
            embed=self.build_embed(), view=self
        )

    @discord.ui.button(emoji="<a:arrow_right:1463262135806328965>", style=discord.ButtonStyle.gray)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < self.max_page:
            self.page += 1
        await interaction.response.edit_message(
            embed=self.build_embed(), view=self
        )

    @discord.ui.button(emoji="<a:darrow_right_big:1474535621216305302>", style=discord.ButtonStyle.gray)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = self.max_page
        await interaction.response.edit_message(
            embed=self.build_embed(), view=self
        )
        
    @discord.ui.button(label="Toggle Sort", style=discord.ButtonStyle.green)
    async def toggle_sort(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.sort_mode = "worst" if self.sort_mode == "best" else "best"

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self
        )
        
class DifficultySelect(discord.ui.Select):
    def __init__(self, current=''):
        options = [
            discord.SelectOption(label="All", value="all"),
            discord.SelectOption(label="Easy", value="easy"),
            discord.SelectOption(label="Hard", value="default"),
            discord.SelectOption(label="Challenges", value="challenges"),
        ]

        super().__init__(
            placeholder="Filter Difficulty/Campaign",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        view: LeaderboardView = self.view
        view.difficulty = self.values[0]
        view.levels = view.filter_levels()
        view.page = 0
        view.max_page = max(
            0, math.ceil(len(view.levels) / view.per_page) - 1
        )
        for option in self.options:
            option.default = option.default == self.values[0]

        await interaction.response.edit_message(
            embed=view.build_embed(),
            view=view
        )

class PlayerCountSelect(discord.ui.Select):
    def __init__(self, current=''):
        options = [discord.SelectOption(label=f'Any', value=0)]
        options.extend(
            discord.SelectOption(
                label=f'{i + 1} Players', 
                value=i + 1,
            )
            for i in range(8)
        )

        super().__init__(
            placeholder="Filter Player Count",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        view: LeaderboardView = self.view
        view.player_count = self.values[0]
        print(self.values[0])
        view.levels = view.filter_levels()
        view.page = 0
        view.max_page = max(
            0, math.ceil(len(view.levels) / view.per_page) - 1
        )

        await interaction.response.edit_message(
            embed=view.build_embed(),
            view=view
        )
        
class Disquda(commands.Cog, name="CrossSquda"):
    def __init__(self, bot) -> None:
        self.bot = bot
    
    def format_time(self, t: float) -> str:
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        ms = int((t - int(t)) * 1000)

        if h > 0:
            return f"{h:02}:{m:02}:{s:02}:{ms:03}"
        else:
            return f"{m:02}:{s:02}:{ms:03}"

    def pretty_level_name(self, name: str) -> str:
        # Replace difficulty prefix
        if name.startswith("Default:"):
            name = "Hard: " + name[len("Default:"):]
        elif name.startswith("Easy:"):
            name = "Easy: " + name[len("Easy:"):]

        # Remove internal suffix
        if name.endswith("_squdaPB"):
            name = name[:-8]

        # Replace underscores with spaces
        return name.replace("_", " ")
        
    @commands.hybrid_command(
        name="scores_leaderboard",
        description="show the leaderboard for best scores on co-op levels",
        aliases=["sc_lb"],
    )
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def leaderboard(self, context: Context):
        try:
            timeout = aiohttp.ClientTimeout(total=5)  # don't hang forever
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f'{URL}/api/get_scores') as resp:
                    if resp.status != 200:
                        await context.send("failed to fetch leaderboard")
                        return

                    data = await resp.json()

        except aiohttp.ClientConnectorError:
            await context.send(
                "leaderboard server is currently offline. try again later."
            )
            return

        except asyncio.TimeoutError:
            await context.send(
                "leaderboard server took too long to respond."
            )
            return

        except aiohttp.ClientError as e:
            # any other HTTP-related issue
            await context.send("failed to fetch leaderboard.")
            print(f"[Leaderboard error] {e}")
            return

        # ---------------- normal logic continues ----------------

        if not data:
            await context.send("No scores yet!")
            return
        view = LeaderboardView(
            context,
            data,
            self.format_time,
            self.pretty_level_name
        )

        await context.send(
            embed=view.build_embed(),
            view=view
        )   
    
    @commands.hybrid_command(
        name="link_bombsquda",
        description=(
            "links your BombSquda ID to your discord"
            "PS. ONLY USE IN DMS!!"
        )
    )
    async def link_bombsquda(self, ctx, bs_id: str):
        # basic sanity check
        if ctx.guild is not None:
            await ctx.reply("Dumbass")
            return
        if ":" not in bs_id or len(bs_id) < 20:
            await ctx.reply("that doesn't look like a ID.")
            return

        self.bot.set_value(ctx.author.id, "squda_id", bs_id)
        await ctx.reply(
            (
                "the id was successfully linked!\nPS. don't share it to anyone, "
                "or they could control certain things!"
            )
        )
    @commands.hybrid_command(
        name="get_bank",
        description="Gets how much of a currency you have in the server's bank.",
    )
    async def test_getcur(self, ctx, currency: str):
        id = self.get_value(ctx.author.id, "squda_id", '')
        if not id:
            await ctx.reply('hey get a squda id first please!')
            return
        data = {
            "bs_id": id,
            "type": currency,
        }
        request = urllib.request.Request(
            f"{URL}/getcur",
            data=json.dumps(data).encode('utf-8'),
            headers={
                "Content-Type": "application/json"
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=2) as response:
                read = response.read()
                thefuckingjson = json.loads(read.decode('utf-8'))
                await ctx.reply(f'you have {thefuckingjson.get('amount')} {currency} in the bank')
        except urllib.error.URLError as e:
            await ctx.reply('couldn\'t connect to the server, try again later')
    
    @commands.hybrid_command(
        name="deposit_bank",
        description="Send a amount to your account in the server's bank.",
    )
    async def deposit_bank(self, ctx, amount: int, currency: str):
        id = self.get_value(ctx.author.id, "squda_id", '')
        player_amount = self.get_value(ctx.author.id, currency, 0)
        if not id:
            await ctx.reply('hey get a squda id first please!')
            return
        if amount > player_amount:
            await ctx.reply(f'you don\'t have enough {currency} to deposit.')
            return
        if amount <= 0:
            await ctx.reply('enter a correct value!')
            return
        data = {
            "bs_id": id,
            "amount": amount,
            "type": currency,
        }
        request = urllib.request.Request(
            f"{URL}/sendcur",
            data=json.dumps(data).encode('utf-8'),
            headers={
                "Content-Type": "application/json"
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=2) as response:
                read = response.read()
                thefuckingjson = json.loads(read.decode('utf-8'))
                new = thefuckingjson.get('new_bal')
                self.bot.add_value(ctx.author.id, currency, -amount)
                await ctx.reply(f'done! you deposited {amount} {currency}.\nyour bank now has: {new} {currency}.')
        except urllib.error.URLError as e:
            await ctx.reply('unable to connect! server is probably down.')
    
    @commands.hybrid_command(
        name="withdraw_bank",
        description="Withdraw a amount from your bank in the server to your account.",
    )
    async def withdraw_bank(self, ctx, amount: int, currency: str):
        id = self.get_value(ctx.author.id, "squda_id", '')
        data = {
            "bs_id": id,
            "type": currency,
        }
        request = urllib.request.Request(
            f"{URL}/getcur",
            data=json.dumps(data).encode('utf-8'),
            headers={
                "Content-Type": "application/json"
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=2) as response:
                read = response.read()
                thefuckingjson = json.loads(read.decode('utf-8'))
                player_amount = thefuckingjson.get('amount')
        except urllib.error.URLError as e:
            await ctx.reply('unable to connect! server is probably down.')
            return
        if not id:
            await ctx.reply('hey get a squda id first please!')
            return
        if amount > player_amount:
            await ctx.reply(f'you don\'t have enough {currency} to withdraw.')
            return
        if amount <= 0:
            await ctx.reply('enter a correct value!')
            return
        data = {
            "bs_id": id,
            "amount": amount,
            "type": currency,
        }
        request = urllib.request.Request(
            f"{URL}/withdrawcur",
            data=json.dumps(data).encode('utf-8'),
            headers={
                "Content-Type": "application/json"
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=2) as response:
                read = response.read()
                thefuckingjson = json.loads(read.decode('utf-8'))
                new = thefuckingjson.get('new_bal')
                self.bot.add_value(ctx.author.id, currency, amount)
                await ctx.reply(f'done! you withdrew {amount} {currency}.\nyour bank now has: {new} {currency}.')
        except urllib.error.URLError as e:
            await ctx.reply('unable to connect! server is probably down.')
    
    @commands.hybrid_command(
        name="ping_server",
        description="Pings the BombSquda server. You'd never have guessed."
    )
    async def ping_server(self, ctx):
        online = False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(URL, timeout=2):
                    online = True
        except Exception as e:
            online = False
        if online:
            await ctx.reply('yeah server seems to be okay')
        else:
            await ctx.reply('server is in fact, not online')
        
            
    @commands.hybrid_command(
        name="unlink_bombsquda",
        description="removes the ID that you linked to your discord account."
    )
    async def unlink_bombsquda(self, ctx):
        self.bot.set_value(ctx.author.id, "squda_id", None)
        await ctx.reply("done! the previous ID was removed.")

async def setup(bot) -> None:
    await bot.add_cog(Disquda(bot))