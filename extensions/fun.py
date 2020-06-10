import discord
import bigbeans

from extensions.models import menuclasses
from discord.ext import commands, menus


class Fun(commands.Cog):

    def __init__(self, bot):
        self.bot = bot  # type: commands.Bot
        self.session = bot.session

    async def before_ready(self):
        self.db = self.bot.db  # type: bigbeans.databean.Databean

    @commands.cooldown(2, 30, commands.BucketType.user)
    @commands.command()
    async def cat(self, ctx):
        """Shows you a bunch of cats."""

        url = "https://api.thecatapi.com/v1/images/search?limit=10"
        headers = {"x-api-key": self.bot.config["external"]["cat_api_key"]}
        async with self.session.get(url, headers=headers) as resp:
            if resp.status == 200:
                results = await resp.json()
            else:
                return await ctx.send("No cats found! The API configuration may be incorrect.")

        # build embed from cat urls
        cat_urls = [item["url"] for item in results]
        cat_embeds = []
        for url in cat_urls:
            embed = discord.Embed(color=16202876)
            embed.set_image(url=url)
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            cat_embeds.append(embed)

        # start menu
        pages = menuclasses.EmbedPageMenu(cat_embeds, formatter=menuclasses.title_page_number_formatter("Cats"))
        menu = menus.MenuPages(pages, timeout=90)
        await menu.start(ctx)


def setup(bot):
    fun_cog = Fun(bot)
    fun_cog.cat.enabled = bot.config["external"]["use_cat_api"]  # disable command if not using API
    bot.add_cog(fun_cog)
