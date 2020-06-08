import collections
import random

from collections import defaultdict

import discord
import bigbeans
import pendulum

from discord.ext import commands, menus
from extensions.models import exceptions, menuclasses

# True represents a "dark" outcome, while False indicates a "light" outcome
VALID_DISPOSITION_MAPPING = {
    "light": False,
    "darkness": True,
    "day": False,
    "night": True,
    "dawn": False,
    "dusk": True,
    "sunrise": False,
    "sunset": True,
    "sunup": False,
    "sundown": True,
    "sunlight": False,
    "moonlight": True
}

MOON_OUTCOMES = [
    {"id": 1, "emoji": "🌛", "negative": False, "message": "Joyful innocence."},
    {"id": 2, "emoji": "🌕", "negative": False, "message": "A gentle warmth."},
    {"id": 3, "emoji": "🌝", "negative": False, "message": "A sweet smile."},
    {"id": 1, "emoji": "🌒", "negative": True, "message": "A sinister energy resounds."},
    {"id": 2, "emoji": "🌑", "negative": True, "message": "Absolution in darkness."},
    {"id": 3, "emoji": "🌚", "negative": True, "message": "Power - but over whom?"},
]

temp = {
    ((1, 2, 3), (True, True, True)): {"value_increase": 5, "message": "Power, but at what cost?"},
    ((1, 2, 3), (False, False, False)): {"value_increase": 5, "message": "Hopeful and content."},
    ((3, 3, 3), (True, True, True)): {"value_increase": 3, "message": "Monsters and beasts - but are they real?"},
    ((3, 3, 3), (False, False, False)): {"value_increase": 3, "message": "At peace."},
    ((2, 2, 2), (True, True, True)): {"value_increase": 6, "message": "Strong, but vulnerable."},
    ((2, 2, 2), (False, False, False)): {"value_increase": 6, "message": "Courage."},
    ((1, 1, 1), (True, True, True)): {"value_increase": 1, "message": "The conquerer of the night fears sunrise."},
    ((1, 1, 1), (False, False, False)): {"value_increase": 1, "message": "Abundance."},
    ((1, 2, 3), (True, False, True)): {"value_increase": 2, "message": "A glimmer of light remains."},
    ((1, 2, 3), (False, True, False)): {"value_increase": 2, "message": "The shadows dance."},
    ((3, 2, 1), (True, False, True)): {"value_increase": 4, "message": "Crush those who oppose you."},
    ((3, 2, 1), (False, True, False)): {"value_increase": 4, "message": "Daylight approaches."},
    ((3, 2, 1), (True, True, True)): {"value_increase": 7, "message": "The final seal is broken."},
    ((3, 2, 1), (False, False, False)): {"value_increase": 7, "message": "It is finished."}
}

BONUS_OUTCOMES = defaultdict(lambda: {"value_increase": 0, "message": "Nothing lost, nothing gained."})
BONUS_OUTCOMES.update(temp)

COIN = "<:crabcoin:719040455886766358>"

DAYLIGHT_STEPS = collections.deque(["🌚", "🌑", "🌑", "☀️", "☀️", "☀️", "🌞", "☀️", "☀️", "☀️", "🌑", "🌑", "🌚"])

# should i move this to toml?
GENERIC_ITEM_MAPPING = {
    "twig": {
        "value": 1,
        "description": (
            "A small innocent-looking twig. It's not worth much on its own, but there's a chance it could be useful "
            "when combined with something else. Maybe it could be used to light a fire?"
        )
    },
    "pebble": {
        "value": 1,
        "description": (
            "A relatively generic pebble. It looks like a perfect skipping stone, but merchants typically "
            "don't buy stones just to throw them, so it'll be a hard sell. It'd be worth more if you did "
            "something with it. "
        )
    },
    "blade of grass": {
        "value": 1,
        "description": (
            "A very green blade of grass fetched from the ground beneath you. Since grass is abundant, it's worth "
            "very little, but it seems springy enough to make some primitive string or bindings."
        )
    },
    "branch": {
        "value": 3,
        "description": (
            "A fallen branch from a nearby tree. It's much larger than a twig, and could be fashioned into a sturdy "
            "handle or rod with the right tools. You could potentially carve it into some kind of weapon."
        )
    },
    "rock": {
        "value": 3,
        "description": (
            "A round-ish rock with both a flat and rough side. It's too heavy for you to pick up, but you can roll "
            "it around to take it with you. If you were to prop it up somewhere it would be a useful (albeit "
            "primitive) workbench."
        )
    },
    "primitive workbench": {
        "value": 5,
        "description": (
            "A large rock propped up on a pile of pebbles. The rough side can be used to sharpen or sand "
            "any number of things, while the flat side can be used as a table of sorts."
        )
    },
    "berry": {
        "value": 2,
        "description": (
            "A small round berry. It looks quite ripe, and hopefully it isn't poisonous. Since it's a form of "
            "nutrition, it would be worth keeping around in the event that you need a snack."
        )
    },
    "apple": {
        "value": 3,
        "description": (
            "A red apple of a modest size. It looks both juicy and quite nutritious. It would be worth keeping "
            "around so that you have something to eat, but a merchant would probably be happy to buy them."
        )
    },
}


class Currency(commands.Cog, name="Currency & Items"):

    def __init__(self, bot):
        self.bot = bot  # type: commands.Bot

    async def add_currency(self, user_id: int, amount: int):
        current = await self.db["currency"].find_one(user_id=user_id)
        if current:
            await self.db["currency"].upsert(["user_id"], user_id=user_id, amount=current["amount"] + amount)
        else:
            await self.db["currency"].insert(user_id=user_id, amount=amount)

    async def before_ready(self):
        self.db = self.bot.db  # type: bigbeans.databean.Databean

    @commands.command(aliases=["$"])
    async def balance(self, ctx, *, who: discord.Member = None):
        """Display the balance of you or another user."""

        who = who or ctx.author
        currency = await self.db["currency"].find_one(user_id=who.id)
        amount_owned = currency["amount"] if currency else 0
        embed = discord.Embed(title="Currency", color=16202876)
        embed.set_author(name=str(who), icon_url=who.avatar_url)
        if ctx.author.id == who.id:
            embed.description = f"You have {amount_owned} {COIN}"
        else:
            embed.description = f"{who.name.capitalize()} has {amount_owned} {COIN}"

        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/644479051918082050/719149475909730354/3dgifmaker92.gif"
        )

        await ctx.send(embed=embed)

    @commands.command()
    async def daily(self, ctx, *, disposition: str):
        """Choose between the forces of light and dark for a chance to earn an extremely high amount of currency.
        Three Fates will be chosen randomly, and if they match the disposition you choose, you will earn a large amount more money.
        Certain combinations of fates will also yield bonus currency.
        Ultimately, the Fates are up to chance. Embrace them."""

        if not disposition.lower() in VALID_DISPOSITION_MAPPING:
            raise commands.BadArgument

        cooldown = await ctx.cogs["Database"].cooldown_query(ctx.author.id, "daily", pendulum.Duration(hours=13))
        if cooldown:
            raise exceptions.OnExtendedCooldown(cooldown)

        results = [
            random.choice(random.shuffle(MOON_OUTCOMES) or MOON_OUTCOMES),
            random.choice(random.shuffle(MOON_OUTCOMES) or MOON_OUTCOMES),
            random.choice(random.shuffle(MOON_OUTCOMES) or MOON_OUTCOMES)
        ]

        is_dark = len(list(filter(lambda k: k["negative"] is True, results))) > 1
        disposition_text = "Dark" if is_dark else "Light"
        disposition_matching = VALID_DISPOSITION_MAPPING[disposition.lower()] is is_dark
        if disposition_matching:
            base_value = 20 + sum((item["id"] * 10 for item in results))
        else:
            base_value = 40 + sum((item["id"] * 12 for item in results))

        id_sequence, disposition_sequence = [item["id"] for item in results], [item["negative"] for item in results]
        bonus_data = BONUS_OUTCOMES[(tuple(id_sequence), tuple(disposition_sequence))]
        disposition_bonus = 4 if disposition_matching else .3
        resulting_value = int((base_value + base_value * bonus_data["value_increase"]) * disposition_bonus)
        message = (
            f"Disposition: {disposition_text} - *{'Harmony' if disposition_matching else 'Conflict'}* \n\n"
            f"Fate I: {results[0]['emoji']} - *{results[0]['message']}*\n"
            f"Fate II: {results[1]['emoji']} - *{results[1]['message']}*\n"
            f"Fate III: {results[2]['emoji']} - *{results[2]['message']}*\n"
            f"Bonus: {bonus_data['value_increase'] * 100}% - *{bonus_data['message']}*"
        )

        embed = discord.Embed(title="You hold your breath and pray...", description=message, color=16202876)
        embed.add_field(name="Final results", value=f"{resulting_value} {COIN}", inline=False)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        embed.set_footer(text="You can play again tomorrow.")

        await self.add_currency(ctx.author.id, resulting_value)
        await ctx.cogs["Database"].cooldown_set(ctx.author.id, "daily")
        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True, ignore_extra=False)
    async def inventory(self, ctx):
        """Displays your inventory."""

        results = await self.db["inventory"].find(user_id=ctx.author.id)
        if not results:
            await ctx.send("You don't have any items!")
        else:
            sorted_results = sorted(results, key=lambda k: k["name"])
            embeds = []
            for data in sorted_results:
                embed = discord.Embed(
                    title=data["name"].capitalize() or "(No item name - how did you get here?)",
                    description=data["description"] or "(No extended description)", color=16202876
                )

                embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
                embed.add_field(
                    name="Quantity",
                    value=(
                        f"You have {data['quantity'] or 1}x of this item, worth a total of "
                        f"{(data['quantity'] or 1) * (data['value'] or 0)} {COIN} ({data['value'] or 0} {COIN} each) "),
                    inline=False
                )

                embeds.append(embed)

            pages = menuclasses.EmbedPageMenu(embeds)
            menu = menus.MenuPages(pages, timeout=90)
            await menu.start(ctx)

    @inventory.command(name="list")
    async def inventory_list(self, ctx):
        results = await self.db["inventory"].find(user_id=ctx.author.id)
        if not results:
            await ctx.send("You don't have any items!")
        else:
            sorted_results = sorted(results, key=lambda k: k["name"])
            page_data = [f"{data['quantity']}x **{data['name'].capitalize()}**" for data in sorted_results]
            pages = menuclasses.ListPageMenu(
                page_data, 10, menuclasses.title_page_number_formatter("Inventory")
            )

            menu = menus.MenuPages(pages, timeout=90)
            await menu.start(ctx)

    @commands.command(aliases=["forage"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def gather(self, ctx):
        await ctx.cogs["Database"].game_advance_time(ctx.author.id, 20)
        current_time = (await ctx.db["game_time"].find_one(user_id=ctx.author.id))["minutes"]
        # implement "don't do stupid shit" logic here; for now being able to gather whenever is okay
        gathered = random.choices(
            ["twig", "pebble", "blade of grass", "branch", "rock", "berry", "apple"],
            weights=[2, 3, 4, 1, 1, 1, 1], k=3
        )

        kept = collections.Counter(gathered[:random.randint(1, 3)])  # don't keep all of it
        obtained = [f"• {count}x **{name.capitalize()}**" for name, count in kept.items()]

        emoji_time_display = DAYLIGHT_STEPS.copy()
        emoji_time_display.rotate(-int((current_time / 1440) * 13))
        duration = pendulum.duration(minutes=current_time)
        hours_truncated = duration.hours - 12 if duration.hours > 12 else duration.hours
        time_printable = f"{str(hours_truncated).zfill(2)}:{str(duration.minutes).zfill(2)}"
        time_suffix = "AM" if 0 < current_time < 719 else "PM"

        embed = discord.Embed(color=16202876)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        embed.description = (
            f"{' '.join(list(emoji_time_display)[:5])}\n"
            f"The current time is {time_printable} {time_suffix}. You spent 20 minutes foraging and found:\n\n"
            "{0}".format("\n".join(obtained))
        )

        for name, count in kept.items():
            to_insert = GENERIC_ITEM_MAPPING[name]
            await ctx.cogs["Database"].inventory_add(
                user_id=ctx.author.id, name=name, description=to_insert["description"], quantity=count,
                value=to_insert["value"]
            )

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Currency(bot))
