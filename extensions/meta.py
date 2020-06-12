import sys
import pkg_resources

import psutil
import discord
import bigbeans

from discord.ext import commands


class Meta(commands.Cog):

    def __init__(self, bot):
        self.bot = bot  # type: commands.Bot
        self.process = psutil.Process()

    async def before_ready(self):
        self.db = self.bot.db  # type: bigbeans.databean.Databean

    @commands.command()
    async def info(self, ctx):
        "Displays various bits of information about the bot."

        embed = discord.Embed(title="Bot information", color=16202876)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

        memory_usage = "``N/A``"
        cpu_usage = "``N/A``"

        # get stats
        try:
            memory_usage = self.process.memory_full_info().uss / 1024 ** 2
            cpu_usage = self.process.cpu_percent() / psutil.cpu_count()
        except psutil.AccessDenied:  # no permissions
            pass

        # this is ugly; i'm not sure if i care
        embed.add_field(name="Developer", value="Kaylynn#444")
        embed.add_field(name="Uptime", value=self.bot._start_time.diff_for_humans(absolute=True))
        embed.add_field(name="Latency", value=f"{self.bot.latency * 1000:.2f} ms")
        embed.add_field(name="Github", value="[kaylynn234/LobsteroRedux](https://github.com/kaylynn234/LobsteroRedux)")
        embed.add_field(name="Support server", value="[support.lobstero.xyz](http://support.lobstero.xyz)")
        embed.add_field(name="Bot invite link", value="[invite.lobstero.xyz](http://invite.lobstero.xyz)")
        embed.add_field(name="Guilds", value=len(self.bot.guilds))
        embed.add_field(name="Library", value=f"Discord.py {pkg_resources.get_distribution('discord.py').version}")
        embed.add_field(name="Process", value=f"{memory_usage} MB RAM & {cpu_usage}% CPU")
        embed.set_footer(text=f"Python v{sys.version.split(' ')[0]}", icon_url="https://i.imgur.com/5BFecvA.png")

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Meta(bot))
