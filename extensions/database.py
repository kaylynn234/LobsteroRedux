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
    # durability: int, the durability of this item (this ties into tool stuff)
    async def inventory_add(self, user_id: int, name: str, durability: int = 0):
        await self.db["inventory"].insert(user_id=user_id, name=name, durability=durability)

    async def inventory_remove(self, user_id: int, name: str, quantity: int):
        # because postgresql is stupid and i can't be fucked dealing with it at midnight i'm going to do this a bad way
        results = await self.db["inventory"].find(user_id=user_id, name=name)
        ids = [str(_id["_id"]) for _, _id in zip(range(quantity), results)]  # dumb way to get only x ids
        query = (
            f"""DELETE FROM inventory
            WHERE _id IN ({', '.join(ids)})"""
        )

        await self.db.execute_query(query)

    # extended_cooldown schema:
    # unique_id: int, this is the "owner" of this cooldown
    # cooldown_group: text, this is the "group" that the cooldown belongs to - mainly an ease-of-use thing
    # last_accessed: tz-aware pendulum timestamp as text, this is the date that the cooldown was last triggered

    async def cooldown_query(self, unique_id: int, cooldown_group: str, duration: pendulum.Duration) -> Union[bool, pendulum.Period]:
        """
        Return False if unique_id is not on cooldown, or time remaining if it is.
        """

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
        """
        Sets a cooldown for unique_id in the specified group.
        """

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
