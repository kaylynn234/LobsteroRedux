import sys
import pkg_resources

import psutil
import discord
import bigbeans

from discord.ext import commands, menus
from extensions.models import menuclasses


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

        memory_usage = 0
        cpu_usage = 0

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
        embed.add_field(name="Process", value=f"{memory_usage:.2f} MB RAM & {cpu_usage:.2f}% CPU")
        embed.set_footer(text=f"Python v{sys.version.split(' ')[0]}", icon_url="https://i.imgur.com/5BFecvA.png")

        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.group(invoke_without_command=True, ignore_extra=False)
    async def lock(self, ctx):
        """A base command for all lock-related subcommands.
        If no subcommand is used, displays a list of locked channels.
        Regardless of this server's locked channels, these commands can always be used."""

        results = await self.db["channel_locks"].find(guild_id=ctx.guild.id)
        if not results:
            return await ctx.send("No locked channels set on this server.")

        mentions = [f"<#{result['channel_id']}>" for result in results]
        pages = menuclasses.ListPageMenu(
            mentions, 10, menuclasses.title_page_number_formatter("Locked channels")
        )

        # start menu with built data
        menu = menus.MenuPages(pages, timeout=90)
        await menu.start(ctx)


    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @lock.command(name="add")
    async def lock_add(self, ctx, *, channel: discord.TextChannel = None):
        """Adds this channel to the list of locked channels.
        If any locked channels are set, the bot will be unable to be used in any non-locked channels.
        Note that regardless of this server's locked channels, these commands can always be used."""

        channel = channel or ctx.channel
        await self.db["channel_locks"].upsert(["guild_id", "channel_id"], guild_id=ctx.guild.id, channel_id=channel.id)
        await ctx.send(f"Locked bot usage to {channel.mention}.")

    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @lock.command(name="remove")
    async def lock_remove(self, ctx, *, channel: discord.TextChannel = None):
        """Removes this channel from the list of locked channels.
        If any locked channels are set, the bot will be unable to be used in any non-locked channels.
        Note that regardless of this server's locked channels, these commands can always be used."""

        channel = channel or ctx.channel
        await self.db["channel_locks"].delete(guild_id=ctx.guild.id, channel_id=channel.id)
        await ctx.send(f"Removed {channel.mention} from the list of locked channels.")


def setup(bot):
    bot.add_cog(Meta(bot))
