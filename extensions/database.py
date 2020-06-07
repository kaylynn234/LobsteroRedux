from typing import Union
import bigbeans
import pendulum

from discord.ext import commands


class Database(commands.Cog):

    def __init__(self, bot):
        self.bot = bot  # type: commands.Bot

    async def before_ready(self):
        self.db = self.bot.db  # type: bigbeans.databean.Databean

    # these are all extremely thin wrappers - i'm not sure i want to keep them
    async def inventory_add(self, user_id: int, name: str, description: str, quantity: int, value: int):
        self.db["inventory"].upsert(
            ["user_id", "name", "description, quantity", "value"],
            user_id=user_id, name=name, description=description, quantity=quantity, value=value
        )

    async def inventory_find_one(self, **kwargs):
        return self.db["inventory"].find_one(**kwargs)

    async def inventory_find(self, **kwargs):
        return self.db["inventory"].find(**kwargs)

    async def inventory_remove(self, **kwargs):
        self.db["inventory"].delete(**kwargs)

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


def setup(bot):
    bot.add_cog(Database(bot))
