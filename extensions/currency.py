import collections

import asyncio
import random

from collections import defaultdict
from enum import Enum


import discord
import toml
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

# there are more efficient ways to do this but i'm too tired to care
DAYLIGHT_STEPS = collections.deque([
    "🌑", "🌑", "🌑", "🌑", "🌑", "🌑",
    "☀️", "☀️", "☀️", "☀️", "☀️", "☀️",
    "☀️", "☀️", "☀️", "☀️", "☀️", "☀️",
    "☀️", "🌑", "🌑", "🌑", "🌑", "🌑"
])

MOON_WHEELS = collections.deque([
    "🌑",
    "🌒",
    "🌓",
    "🌔",
    "🌕",
    "🌖",
    "🌗",
    "🌘"
])

MOON_WHEEL_INFO = {
    "🌑": {"message": "Cold, eerie darkness.", "amount": 5},
    "🌒": {"message": "A hint of warmth.", "amount": 20},
    "🌓": {"message": "Hope amidst the night.", "amount": 45},
    "🌔": {"message": "An uneasy light.", "amount": 65},
    "🌕": {"message": "Blinding light.", "amount": 120},
    "🌖": {"message": "Comfort with a hint of despair.", "amount": 65},
    "🌗": {"message": "A cool breeze laden with secrets.", "amount": 45},
    "🌘": {"message": "Worry plagues the mind.", "amount": 30}
}


with open("extensions/items.toml") as tomlfile:
    item_data = toml.load(tomlfile)
    ITEM_MAPPING = defaultdict(lambda: item_data["item 404"])
    ITEM_MAPPING.update(item_data)


class ActionOutcome(Enum):
    NORMAL = 1
    ATTACKED = 2
    VICTORIOUS = 3


class Currency(commands.Cog, name="Currency & Items"):

    def __init__(self, bot):
        self.bot = bot  # type: commands.Bot

    def calculate_time_details(self, current_time):
        emoji_time_display = DAYLIGHT_STEPS.copy()
        emoji_time_display.rotate(-int((current_time / 1440) * 24))
        fuck_pendulum = pendulum.now().start_of("day").add(minutes=current_time)
        time_printable = fuck_pendulum.strftime("%I:%M %p")

        return emoji_time_display, time_printable

    async def add_currency(self, user_id: int, amount: int):
        current = await self.db["currency"].find_one(user_id=user_id)
        if current:
            await self.db["currency"].upsert(["user_id"], user_id=user_id, amount=current["amount"] + amount)
        else:
            await self.db["currency"].insert(user_id=user_id, amount=amount)

    async def before_ready(self):
        self.db = self.bot.db  # type: bigbeans.databean.Databean

    @commands.is_owner()
    @commands.command()
    async def giveme(self, ctx, amount: int, *, item):
        for _ in range(amount):
            await ctx.cogs["Database"].inventory_add(user_id=ctx.author.id, name=item, durability=100)

    @commands.command(aliases=["$"])
    async def balance(self, ctx, *, who: discord.Member = None):
        """
        Display the balance of you or another user.
        """

        # get user, amount and then build embed
        who = who or ctx.author
        currency = await self.db["currency"].find_one(user_id=who.id)
        amount_owned = currency["amount"] if currency else 0
        embed = discord.Embed(title="Currency", color=16202876)
        embed.set_author(name=str(who), icon_url=who.avatar_url)

        # choose phrasing
        if ctx.author.id == who.id:
            embed.description = f"You have {amount_owned} {COIN}"
        else:
            embed.description = f"{who.name.capitalize()} has {amount_owned} {COIN}"

        # embed felt too empty otherwise
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/644479051918082050/719149475909730354/3dgifmaker92.gif"
        )

        await ctx.send(embed=embed)

    @commands.command()
    async def daily(self, ctx, *, disposition: str):
        """
        Choose between the forces of light and dark for a chance to earn an extremely high amount of currency.
        Three Fates will be chosen randomly, and if they match the disposition you choose, you will earn a large amount more money.
        Certain combinations of fates will also yield bonus currency.
        Ultimately, the Fates are up to chance. Embrace them.
        """

        if not disposition.lower() in VALID_DISPOSITION_MAPPING:
            raise commands.BadArgument

        # query the cooldown, error if they can't play
        cooldown = await ctx.cogs["Database"].cooldown_query(ctx.author.id, "daily", pendulum.Duration(hours=13))
        if cooldown:
            raise exceptions.OnExtendedCooldown(cooldown)

        # choose us some outcomes
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

        # decide monetary output and build embed message
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

        # build embed
        embed = discord.Embed(title="You hold your breath and pray...", description=message, color=16202876)
        embed.add_field(name="Final results", value=f"{resulting_value} {COIN}", inline=False)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        embed.set_footer(text="You can play again tomorrow.")

        # give them their money and send
        await self.add_currency(ctx.author.id, resulting_value)
        await ctx.cogs["Database"].cooldown_set(ctx.author.id, "daily")
        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True, ignore_extra=False)
    async def inventory(self, ctx):
        """
        Displays your inventory.
        """

        # fetch items; if they don't have any, don't bother
        results = await self.db["inventory"].find(user_id=ctx.author.id)
        if not results:
            await ctx.send("You don't have any items!")
        else:
            sorted_results = collections.Counter([item["name"] for item in sorted(results, key=lambda k: k["name"])])
            embeds = []
            for name, count in sorted_results.items():
                item_details = ITEM_MAPPING[name]
                embed = discord.Embed(
                    title=name,
                    description=item_details["description"] or "(No extended description)", color=16202876
                )

                # build embed content
                embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
                embed.add_field(
                    name="Quantity",
                    value=(
                        f"You have {count}x of this item, worth a total of "
                        f"{count * (item_details['value'] or 0)} {COIN} ({item_details['value'] or 0} {COIN} each) "),
                    inline=False
                )

                embeds.append(embed)

            # start menu
            pages = menuclasses.EmbedPageMenu(embeds)
            menu = menus.MenuPages(pages, timeout=90)
            await menu.start(ctx)

    @inventory.command(name="list")
    async def inventory_list(self, ctx):
        """
        Displays your inventory in a list without extra information.
        """

        # fetch items; if they don't have any, don't bother
        results = await self.db["inventory"].find(user_id=ctx.author.id)
        if not results:
            await ctx.send("You don't have any items!")
        else:
            # sort alphabetically by item name, then build data for our menu
            sorted_results = collections.Counter([item["name"] for item in sorted(results, key=lambda k: k["name"])])
            page_data = [f"{count}x **{name.capitalize()}**" for name, count in sorted_results.items()]
            pages = menuclasses.ListPageMenu(
                page_data, 10, menuclasses.title_page_number_formatter("Inventory")
            )

            # start menu with built data
            menu = menus.MenuPages(pages, timeout=90)
            await menu.start(ctx)

    @commands.command(aliases=["forage"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def gather(self, ctx):
        """
        Go in search of valuables.
        """

        await ctx.cogs["Database"].game_advance_time(ctx.author.id, 20)
        current_time = (await ctx.db["game_time"].find_one(user_id=ctx.author.id))["minutes"]
        emoji_time_display, time_printable = self.calculate_time_details(current_time)

        # appease the linter
        strongest_weapon = None
        strongest_weapon_db_entry = None
        durability_lost = None
        bonus = 0
        outcome = ActionOutcome.NORMAL

        # "don't do stupid shit" logic
        if (0 < current_time < 330) or (1110 < current_time < 1440):
            if random.randint(1, 3) == 3:
                outcome = ActionOutcome.ATTACKED
                # get weapons, check if we can defeat this monster
                # i would've liked to do this differently, but can't think of a better method right now
                # first we narrow down to the distinct items that the user owns
                distinct_owned_items = await self.db.fetch_query(
                    f"SELECT DISTINCT on (name) name, user_id FROM inventory WHERE user_id = {ctx.author.id}"
                )

                # now that we have owned items from the db, we get all items that are tools
                # i would want to make this a dict, but it makes the next bits annoying - perhaps there's a better way?
                tools = [(key, value) for key, value in ITEM_MAPPING.items() if value.get("tool", None)]
                # filter that down to all weapons
                weapons = list(filter(lambda k: k[1]["tool"]["tool_type"] == "weapon", tools))
                # now we filter weapons down to weapons we actually have
                distinct_names = [item["name"] for item in distinct_owned_items]
                owned_weapons = [weapon for weapon in weapons if weapon[0] in distinct_names]
                # get the strongest if we own any weapons
                if owned_weapons:
                    strongest_weapon = sorted(owned_weapons, key=lambda k: k[1]["tool"]["strength"], reverse=True)[0]
                    roll = random.randint(1, 2)
                    if strongest_weapon[1]["tool"]["strength"] >= roll:
                        outcome = ActionOutcome.VICTORIOUS
                        bonus = random.randint(6, 13)
                        strongest_weapon_db_entry = await self.db["inventory"].find_one(
                            user_id=ctx.author.id, name=strongest_weapon[0]
                        )

        # in the future i'll do this differently, for now it'll look like this
        gathered = random.choices(
            ["twig", "pebble", "blade of grass", "branch", "rock", "berry", "apple"],
            weights=[2, 3, 4, 1, 1, 1, 1], k=3 + bonus
        )

        kept = collections.Counter(gathered[:random.randint(1, 3)])  # don't keep all of it
        if outcome == ActionOutcome.VICTORIOUS:  # give them a special item
            durability_lost = random.randint(1, 3)
            kept[random.choice(["fang", "cursed bone"])] = 1

        obtained = [f"• {count}x **{name.capitalize()}**" for name, count in kept.items()]

        # build the embed
        embed = discord.Embed(color=16202876)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        if outcome == ActionOutcome.ATTACKED:
            embed.description = (
                f"{' '.join(list(emoji_time_display)[:5])}\n"
                f"The current time is {time_printable}. You spent 20 minutes forag- \n\n"
                "**You were attacked by a beast of the night!** You managed to get away, but you lost "
                "the items that you'd gathered in the process."
            )
        elif outcome == ActionOutcome.VICTORIOUS:
            # maybe get rid of the weapon
            new_durability = strongest_weapon_db_entry["durability"] - durability_lost
            if new_durability <= 0:
                await self.db["inventory"].delete(_id=strongest_weapon_db_entry["_id"])
            else:
                await self.db["inventory"].upsert(
                    ["_id"], _id=strongest_weapon_db_entry["_id"], durability=new_durability
                )

            embed.description = (
                f"{' '.join(list(emoji_time_display)[:5])}\n"
                f"The current time is {time_printable}. You spent 20 minutes forag- \n\n"
                "**You were attacked by a beast of the night!** - but it was no match for you!\n"
                f"Your weapon **{strongest_weapon_db_entry['name']}** (ID ``{strongest_weapon_db_entry['_id']}``) "
                f"lost {durability_lost} point(s) of durability, and you gained:\n\n"
                "{0}".format("\n".join(obtained))
            )
        else:
            embed.description = (
                f"{' '.join(list(emoji_time_display)[:5])}\n"
                f"The current time is {time_printable}. You spent 20 minutes foraging and found:\n\n"
                "{0}".format("\n".join(obtained))
            )

        # only award items if they didn't get attacked
        if outcome != ActionOutcome.ATTACKED:
            # give the user their items
            for name, count in kept.items():
                for _ in range(count):  # TODO: move this to an execute many, will chug later on otherwise
                    await ctx.cogs["Database"].inventory_add(user_id=ctx.author.id, name=name)

        await ctx.send(embed=embed)

    @commands.command(aliases=["nap", "rest"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def sleep(self, ctx):
        """
        Rest through the horrors of the night.
        """

        results = await ctx.db["game_time"].find_one(user_id=ctx.author.id)
        if results:
            current_time = results["minutes"]
        else:
            current_time = 600

        if 390 < current_time < 1050:
            return await ctx.send("You can only sleep at night!")

        # morning simulator 2k20
        new_time = random.choice([560, 580, 600, 620, 640])
        await ctx.db["game_time"].upsert(["user_id"], user_id=ctx.author.id, minutes=new_time)

        # build embed
        emoji_time_display, time_printable = self.calculate_time_details(new_time)
        embed = discord.Embed(color=16202876)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        embed.description = (
            f"{' '.join(list(emoji_time_display)[:5])}\n"
            f"You curl up on the ground and fall asleep. When you wake up again, it's {time_printable}."
            "\nAny beasts that could cause you harm should have departed by now, so going exploring or gathering "
            "materials is probably safe."
        )

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def craft(self, ctx, *, item):
        """
        Use your materials to build something new.
        """

        to_craft = ITEM_MAPPING.get(item.lower(), {}).get("crafting", {})
        if not to_craft:
            return await ctx.send("That's not a craftable item!")

        to_craft["name"] = item.lower()  # helper

        # get inventory, collate counts
        inventory = await self.db["inventory"].find(user_id=ctx.author.id)  # :grimace:
        # i want to make this counting stuff SQL but not sure how to do that yet, will look later
        item_names = [item["name"] for item in inventory]
        item_counts = collections.Counter(item_names)

        # needs a workbench we don't have
        if to_craft["made_with"] and to_craft["made_with"] not in item_counts:
            return await ctx.send(f"You need a **{to_craft['made_with'].capitalize()}** to craft this!")

        # make the item summary
        can_craft = True
        summary = []
        for item in to_craft["ingredients"]:
            if item["amount"] > item_counts[item["name"]]:
                can_craft = False
                delta = item["amount"] - item_counts[item["name"]]
                summary.append(f"❌ {item['amount']}x **{item['name'].capitalize()}**. You need {delta} more!")
            else:
                summary.append(f"✅ {item['amount']}x **{item['name'].capitalize()}**. You have enough of this item!")

        if can_craft:
            # we have everything, so advance time
            await ctx.cogs["Database"].game_advance_time(ctx.author.id, 40)
            current_time = (await ctx.db["game_time"].find_one(user_id=ctx.author.id))["minutes"]
            emoji_time_display, time_printable = self.calculate_time_details(current_time)
            summary.append(f"\n{' '.join(list(emoji_time_display)[:5])}")
            summary.append(
                f"The current time is {time_printable}. "
                f"You spent 40 minutes crafting and made {to_craft['makes']}x **{to_craft['name'].capitalize()}**"
            )
        else:
            summary.append("\nYou're missing items that you need!")

        # build the embed
        embed = discord.Embed(color=16202876)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        embed.description = "\n".join(summary)

        if can_craft:
            # remove items from inventory
            for ingredient in to_craft["ingredients"]:
                await ctx.cogs["Database"].inventory_remove(
                    user_id=ctx.author.id, name=ingredient["name"], quantity=ingredient["amount"]
                )

            # try tool information, :grimace: this is suuuuper ugly
            new_durability = ITEM_MAPPING[to_craft["name"]].get("tool", {"durability": 0})["durability"]

            # add new crafted item to inventory
            # TODO: fix this so that it doesn't chug with many insertions
            for _ in range(to_craft["makes"]):
                await ctx.cogs["Database"].inventory_add(
                    user_id=ctx.author.id, name=to_craft["name"], durability=new_durability
                )

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def craftable(self, ctx):
        """
        What can you craft with your current tools?
        """

        # get inventory so that we know what we can make
        inventory_names = [item["name"] for item in await self.db["inventory"].find(user_id=ctx.author.id)]
        can_be_crafted = []
        for name, data in ITEM_MAPPING.items():
            info = data.get("crafting", None)
            if not info:
                continue

            # it either doesn't require a workbench (False) or we have the workbench that we need
            if info["made_with"] in inventory_names or not info["made_with"]:
                if info["made_with"]:
                    can_be_crafted.append(
                        f"With ``{info['made_with'].capitalize()}``: **{name.capitalize()}**"
                    )
                else:
                    can_be_crafted.append(f"**{name.capitalize()}** (no requirements)")

        # build a menu out of it
        pages = menuclasses.ListPageMenu(
            can_be_crafted, 10, menuclasses.title_page_number_formatter("Craftable with your current tools")
        )

        # start menu with built data
        menu = menus.MenuPages(pages, timeout=90)
        await menu.start(ctx)

    def _generate_spinny_wheel(self, seq):
        """
        Generates a spinny wheel
        """

        result_string = (
            f"🎰⬇️🎰\n"
            f"{seq[7]}{seq[0]}{seq[1]}\n"
            f"{seq[6]}⚙️{seq[2]}\n"
            f"{seq[5]}{seq[4]}{seq[3]}\n"
        )

        return result_string

    @commands.command()
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def spin(self, ctx):
        """
        Spin the Moonlit Wheel in search of wealth!
        """

        # check if they have enough to spin
        currency = await self.db["currency"].find_one(user_id=ctx.author.id)
        amount_owned = currency["amount"] if currency else 0

        if amount_owned < 50:
            return await ctx.send(f"You need at least **50** {COIN} to do this! You have **{amount_owned}** {COIN}")

        # take money away in advance
        await self.add_currency(ctx.author.id, -50)

        wheel = MOON_WHEELS.copy()
        wheel.rotate(random.randint(0, 8))  # these numbers bear no significance whatsoever

        # prepare embed and send the first message
        embed = discord.Embed(title="You hope for the best and spin...", color=16202876)
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)
        embed.description = self._generate_spinny_wheel(wheel)
        message = await ctx.send(embed=embed)

        for i in [2, 2, 2, 1]:
            await asyncio.sleep(.75)
            wheel.rotate(-i)
            embed.description = self._generate_spinny_wheel(wheel)
            if i == 1:  # last step
                field_message = (
                    f"{wheel[0]} - *{MOON_WHEEL_INFO[wheel[0]]['message']}*\n"
                    f"You earned **{MOON_WHEEL_INFO[wheel[0]]['amount']}** {COIN}"
                )

                embed.add_field(name="Outcome", value=field_message)

            await message.edit(embed=embed)

        # finally, give them the money
        await self.add_currency(ctx.author.id, MOON_WHEEL_INFO[wheel[0]]["amount"])


def setup(bot):
    bot.add_cog(Currency(bot))
