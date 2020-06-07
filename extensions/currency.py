import random

from collections import defaultdict

import discord
import bigbeans
import pendulum

from discord.ext import commands
from extensions.models import exceptions

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


class Currency(commands.Cog):

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

    @commands.command()
    async def daily(self, ctx, *, disposition: str):
        """Choose between the forces of light and dark for a chance to earn an extremely high amount of currency.
        Three Fates will be chosen randomly, and if they match the disposition you choose, you will earn a large amount more money.
        Certain combinations of fates will also yield bonus currency.
        Ultimately, the Fates are up to chance. EMbrace them.
        """

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
        embed.set_footer(text="You can play again tomorrow.")
        await self.add_currency(ctx.author.id, resulting_value)
        await ctx.cogs["Database"].cooldown_set(ctx.author.id, "daily")
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Currency(bot))
