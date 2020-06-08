import sys
import itertools
import traceback

import discord
import humanize

from jishaku.meta import __version__
from jishaku.metacog import GroupCogMeta
from jishaku.modules import ExtensionConverter, package_version
from jishaku.paginators import WrappedPaginator
from jishaku.cog_base import JISHAKU_HIDE, JishakuBase
from discord.ext import commands


try:
    import psutil
except ImportError:
    psutil = None


@commands.is_owner()
@commands.group(name="jishaku", aliases=["admin"], hidden=JISHAKU_HIDE, invoke_without_command=True, ignore_extra=False)
async def admin(self, ctx: commands.Context):
    """A suite of owner/ admin commands powered by jsk behind the scenes."""

    summary = [
        f"• Based on Jishaku v{__version__}, running discord.py `{package_version('discord.py')}`.",
        f"• `Python {sys.version}` on `{sys.platform}`.".replace("\n", ""),
        f"• Bot started {self.bot._start_time.diff_for_humans()}.",
    ]

    try:
        proc = psutil.Process()

        with proc.oneshot():
            mem = proc.memory_full_info()
            summary.append(
                f"• {humanize.naturalsize(mem.rss)}; "
                f"{humanize.naturalsize(mem.vms)}; "
                f"{humanize.naturalsize(mem.uss)} (physical, virtual, unique)"
            )

            name = proc.name()
            pid = proc.pid
            thread_count = proc.num_threads()
            summary.append(f"• Running on PID {pid} (`{name}`) with {thread_count} thread(s).")
    except Exception:  # no psutil, no perms, whatever
        pass

    cache_summary = f"{len(self.bot.guilds)} guild(s) and {len(self.bot.users)} user(s)"
    if isinstance(self.bot, discord.AutoShardedClient):
        summary.append(f"• Automatically sharded: can see {cache_summary}.")
    elif self.bot.shard_count:
        summary.append(f"• Manually sharded: can see {cache_summary}.")
    else:
        summary.append(f"• Not sharded: can see {cache_summary}.")

    summary.append(f"• Average websocket latency: {round(self.bot.latency * 1000, 2)}ms.")

    await ctx.send("\n".join(summary))


class Admin(JishakuBase, metaclass=GroupCogMeta, command_parent=admin):
    """A jishaku mixin with tweaked functionality."""

    @commands.command(name="load", aliases=["reload"])
    async def jsk_load(self, ctx: commands.Context, *extensions: ExtensionConverter):
        """Loads or reloads the given extension names.
        Reports any extensions that failed to load."""

        paginator = WrappedPaginator(prefix='', suffix='')

        for extension in itertools.chain(*extensions):
            method, icon = (
                (self.bot.reload_extension, "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}")
                if extension in self.bot.extensions else
                (self.bot.load_extension, "\N{INBOX TRAY}")
            )

            try:
                method(extension)
            except Exception as error:  # pylint: disable=broad-except
                traceback_data = ''.join(traceback.format_exception(type(error), error, error.__traceback__, 1))
                paginator.add_line(
                    f"{icon}\N{WARNING SIGN} `{extension}`\n```py\n{traceback_data}\n```",
                    empty=True
                )
            else:
                paginator.add_line(f"{icon} `{extension}`", empty=True)
                extension_cog_mapping = {cog.__module__: cog for cog in ctx.cogs.values()}
                before_ready = getattr(extension_cog_mapping[extension], "before_ready", None)
                if before_ready:
                    try:
                        await before_ready()
                    except Exception as error:
                        traceback_data = ''.join(traceback.format_exception(type(error), error, error.__traceback__, 1))
                        paginator.add_line(
                            f"{icon}\N{WARNING SIGN} `{extension}`\n```py\n{traceback_data}\n```",
                            empty=True
                        )

        for page in paginator.pages:
            await ctx.send(page)


def setup(bot):
    bot.add_cog(Admin(bot))
