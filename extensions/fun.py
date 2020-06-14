import random
import re

from io import BytesIO

import discord
import bigbeans

from PIL import Image
from extensions.models import menuclasses
from discord.ext import commands, menus


class Fun(commands.Cog):

    def __init__(self, bot):
        self.bot = bot  # type: commands.Bot
        self.session = bot.session

    async def before_ready(self):
        self.db = self.bot.db  # type: bigbeans.databean.Databean

    async def lobstero_api_request(self, ctx, number, group):
        if number:
            url = self.bot.config["external"]["lobstero_api_address"] + f"/specific/{group}/{number}"
        else:
            url = self.bot.config["external"]["lobstero_api_address"] + f"/random/{group}"

        # make a request for an image url
        async with self.session.get(url) as resp:
            if resp.status == 200:
                results = await resp.json()
            else:
                if number:
                    return await ctx.send(f"No {group} with number {number} found!")
                else:
                    return await ctx.send(f"No {group} found! The API may be down or misconfigured.")

        # now get the image and load it into a buffer
        buffer = BytesIO()
        filename = results['item'].split('/')[-1]
        url = self.bot.config["external"]["lobstero_api_address"] + results["item"]
        async with self.session.get(url) as resp:
            image_bytes = await resp.read()

        # make bytesio from received image
        buffer.write(image_bytes)
        buffer.seek(0)
        to_send = discord.File(fp=buffer, filename=filename)

        # build embed
        embed = discord.Embed(color=16202876)
        embed.set_image(url=f"attachment://{filename}")
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        return {"embed": embed, "file": to_send, "response": results}

    @commands.cooldown(2, 30, commands.BucketType.user)
    @commands.command()
    async def cat(self, ctx):
        """Shows you a bunch of cats."""

        url = "https://api.thecatapi.com/v1/images/search?limit=5"
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

    @commands.cooldown(2, 30, commands.BucketType.user)
    @commands.command()
    async def dog(self, ctx):
        """Shows you a bunch of dogs."""

        url = "https://dog.ceo/api/breeds/image/random/5"
        async with self.session.get(url) as resp:
            if resp.status == 200:
                results = await resp.json()
            else:
                return await ctx.send("No dogs found! The API may be down.")

        # build embed from dog urls
        dog_embeds = []
        for url in results["message"]:
            embed = discord.Embed(color=16202876)
            embed.set_image(url=url)
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            dog_embeds.append(embed)

        # start menu
        pages = menuclasses.EmbedPageMenu(dog_embeds, formatter=menuclasses.title_page_number_formatter("Dogs"))
        menu = menus.MenuPages(pages, timeout=90)
        await menu.start(ctx)

    @commands.command()
    async def gnome(self, ctx, *people: discord.Member):
        """Gnome your chums!"""

        people = tuple(person for person in people if person.id != ctx.author.id)
        if not people:
            return await ctx.send("You can't gnome (g)nothing! (or yourself!)")

        if len(people) == 1:
            mention_string = f"{people[0].mention} has"
        elif len(people) == 2:
            mention_string = f"{people[0].mention} and {people[1].mention} have"
        else:
            mention_string = ", ".join([person.mention for person in people[:-1]]) + f" and {people[-1].mention} have"

        # get some gnome stats
        gnome_results = await self.db["action_counts"].find_one(user_id=ctx.author.id, action="gnome")
        current_gnome_count = gnome_results['amount'] if gnome_results else 0

        # build embed
        results = await self.lobstero_api_request(ctx, None, "gnomes")
        gnome_index = results["response"]["index"]
        results["embed"].title = f"{ctx.author.name.capitalize()} gnomes their chums."
        results["embed"].description = (
            f"{mention_string} been gnomed! This is gnome {gnome_index}. So far, {ctx.author.name.capitalize()} has "
            f"gnomed {current_gnome_count + len(people)} {'people' if current_gnome_count else 'person'}."
        )

        # update gnome stats
        await self.db["action_counts"].upsert(
            ["user_id", "gnome"],
            user_id=ctx.author.id, action="gnome", amount=current_gnome_count + len(people)
        )

        await ctx.send(embed=results["embed"], file=results["file"])

    @commands.command()
    async def cursedcat(self, ctx, number: int = None):
        """Sends you a cursed cat image. Most of these donated by the user luggi."""

        results = await self.lobstero_api_request(ctx, number, "cursedcats")
        results["embed"].title = f"Cursed cat #{results['response']['index']}"
        await ctx.send(embed=results["embed"], file=results["file"])

    @commands.command()
    async def conglomerate(self, ctx):
        """Randomized text madness."""

        words = filter(None, [message.clean_content async for message in ctx.channel.history(limit=250)])
        sentence = " ".join(random.choice(list(words)) for _ in range(random.randint(6, 18)))
        await ctx.send(sentence)

    @commands.command(name="88x31", aliases=["31x88"])
    async def eightyeightxthreeone(self, ctx):
        """Grabs a random 88x31 button from https://cyber.dabamos.de/88x31/."""

        async with self.bot.session.get("https://cyber.dabamos.de/88x31/") as resp:
            data = await resp.text()

        # get a list of urls & build embed, then send
        found = re.findall('<img.*?src="(.*?)"[^\>]+>', data)
        embed = discord.Embed(title="88x31", color=16202876)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        embed.set_image(url=f"https://cyber.dabamos.de/88x31/{random.choice(found)}")

        await ctx.send(embed=embed)

    @commands.command()
    async def inspire(self, ctx):
        """Sends you a few "inspiring" quotes."""

        images = []
        for i in range(4):
            async with self.session.get("https://inspirobot.me/api?generate=true") as resp:
                url = await resp.text()

            async with self.session.get(url) as resp:
                image_bytes = BytesIO(await resp.read())

            image_bytes.seek(0)
            images.append(Image.open(image_bytes))

        # would executor this normally, but too lazy and this is a cheap operation
        # definitely a better way to do this, but again, too lazy - i'll patch it up later i promise
        canvas = Image.new("RGBA", (1300, 1300), (0, 0, 0, 0))
        canvas.paste(images[0], (0, 0))
        canvas.paste(images[1], (650, 0))
        canvas.paste(images[2], (0, 650))
        canvas.paste(images[3], (650, 650))

        buffer = BytesIO()
        canvas.save(buffer, format="PNG")
        buffer.seek(0)

        # build embeds and send stuff
        embed = discord.Embed(title="\"Inspiring\" quote(s)", color=16202876)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        embed.set_image(url=f"attachment://inspire.png")
        ready_to_send = discord.File(buffer, "inspire.png")

        await ctx.send(embed=embed, file=ready_to_send)


def setup(bot):
    fun_cog = Fun(bot)
    fun_cog.cat.enabled = bot.config["external"]["use_cat_api"]  # disable command if not using API
    bot.add_cog(fun_cog)
