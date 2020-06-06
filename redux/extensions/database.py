import bigbeans

from discord.ext import commands


class Database(commands.Cog):

    def __init__(self, bot):
        self.bot = bot  # type: commands.Bot

    @commands.Cog.listener("before_ready")
    async def before_ready(self):
        self.db = self.bot.db  # type: bigbeans.databean.Databean

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


def setup(bot):
    bot.add_cog(Database(bot))
