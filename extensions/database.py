from typing import Union
import bigbeans
import pendulum

from discord.ext import commands


def wrap_around(minimum_value, maximum_value, n):
    if minimum_value < n < maximum_value:
        return n
    elif n > maximum_value:
        return minimum_value + n
    else:
        return maximum_value - n


class Database(commands.Cog):

    def __init__(self, bot):
        self.bot = bot  # type: commands.Bot

    async def before_ready(self):
        self.db = self.bot.db  # type: bigbeans.databean.Databean

    # inventory schema:
    # user_id: int, the owner of this item
    # name: text, the name of this item
    # description: text, description of this item
    # quantity: int, amount of this item owned
    # value: int, value in coin per item
    async def inventory_add(self, user_id: int, name: str, description: str, quantity: int, value: int):
        result = await self.db["inventory"].find_one(user_id=user_id, name=name, description=description, value=value)
        if result:
            await self.db["inventory"].upsert(
                ["user_id", "name"],
                user_id=user_id, name=name, description=description, quantity=quantity + result["quantity"], value=value
            )
        else:
            await self.db["inventory"].insert(
                user_id=user_id, name=name, description=description, quantity=quantity, value=value
            )

    async def inventory_remove(self, user_id: int, name: str, description: str, quantity: int, value: int):
        result = await self.db["inventory"].find_one(user_id=user_id, name=name, description=description, value=value)
        if result:
            new_amount = result["quantity"] - quantity
            if new_amount > 0:
                await self.db["inventory"].upsert(
                    ["user_id", "name"],
                    user_id=user_id, name=name, description=description, quantity=new_amount, value=value
                )
            else:
                await self.db["inventory"].delete(user_id=user_id, name=name)

    # extended_cooldown schema:
    # unique_id: int, this is the "owner" of this cooldown
    # cooldown_group: text, this is the "group" that the cooldown belongs to - mainly an ease-of-use thing
    # last_accessed: tz-aware pendulum timestamp as text, this is the date that the cooldown was last triggered

    async def cooldown_query(self, unique_id: int, cooldown_group: str, duration: pendulum.Duration) -> Union[bool, pendulum.Period]:
        """Return False if unique_id is not on cooldown, or time remaining if it is."""

        result = await self.db["extended_cooldown"].find_one(unique_id=unique_id, cooldown_group=cooldown_group)
        if not result:
            return False
        else:
            now = pendulum.now()
            last_accessed = pendulum.parse(result["last_accessed"])  # type: pendulum.DateTime
            delta = now - last_accessed
            if delta > duration:
                return False
            else:
                return last_accessed + duration

    async def cooldown_set(self, unique_id: int, cooldown_group: str) -> None:
        """Sets a cooldown for unique_id in the specified group."""

        now = str(pendulum.now())
        await self.db["extended_cooldown"].upsert(
            ["unique_id", "cooldown_group"], unique_id=unique_id, cooldown_group=cooldown_group, last_accessed=now
        )

    # game_time schema
    # user_id: int, the user the time is relevant to
    # minutes: int, the time in minutes for the user
    async def game_advance_time(self, user_id: int, minutes: int):
        result = await self.db["game_time"].find_one(user_id=user_id)
        if not result:
            await self.db["game_time"].insert(user_id=user_id, minutes=wrap_around(0, 1440, 600 + minutes))
        else:
            await self.db["game_time"].upsert(
                ["user_id"], user_id=user_id, minutes=wrap_around(0, 1440, result["minutes"] + minutes)
            )


def setup(bot):
    bot.add_cog(Database(bot))
