import random
import difflib
import logging
import traceback
import re

from collections import defaultdict
from typing import Sequence, Iterator, Optional, KeysView, MutableMapping

import bigbeans
import discord
import uwuify
import aiohttp

from discord.ext import commands, menus
from . import menuclasses, exceptions

logging.basicConfig(level=logging.INFO)

HELP_ALIASES = [
    "hlep",
    "hpel",
    "pehl",
    "phel",
    "pleh",
    "halp",
    "holp",
    "howolp",
    "huwulp",
    "hilp",
    "hulp",
    "hylp"
    ]


class CustomContext(commands.Context):

    @property
    def db(self):
        return self.bot.db

    @property
    def cogs(self):
        cog_dict = defaultdict(lambda: None)
        return cog_dict.update(self.bot.cogs) or cog_dict


class CustomHelpCommand(commands.HelpCommand):

    def __init__(self):
        self.not_found = None
        super().__init__(command_attrs={"aliases": HELP_ALIASES})

    async def check_and_jumble(self, embed):
        if self.context.invoked_with.lower() in ["halp", "holp", "hilp", "hulp"]:
            tr = str.maketrans(
                "eE",
                f"{self.context.invoked_with[1].lower()}{self.context.invoked_with[1].upper()}"
            )

            embed.description = embed.description.translate(tr)
        elif self.context.invoked_with in ["howolp", "huwulp"]:
            embed.description = uwuify.uwu_text(embed.description)
        elif self.context.invoked_with == "pleh":
            embed.description = " ".join([w[len(w)::-1] for w in embed.description.split(" ")])
        elif self.context.invoked_with == "hylp":
            tr = str.maketrans("aeiou", "yyyyy")
            embed.description = embed.description.translate(tr)
        elif self.context.invoked_with != "help":
            desc = list(embed.description)
            embed.description = "".join(random.shuffle(desc) or desc)

        return embed

    async def usable_commands(self, sequence: Sequence[commands.Command]):
        usable_commands = []

        for command in sequence:
            try:
                usable = await command.can_run(self.context)
            except (commands.CommandInvokeError, commands.CheckFailure):
                usable = False

            if usable:
                usable_commands.append(command)

        return usable_commands

    async def generate_cog_help(self, cog) -> discord.Embed:
        retrieved_commands = cog.get_commands()
        results = await self.usable_commands(retrieved_commands)

        if not results:  # empty list
            return None

        embed = discord.Embed(title="Help", color=16202876)
        description = [
            f"```{cog.qualified_name}```",
            f"{cog.description}\n",
            f"```Commands ({len(results)} available)``` ",
            f"``{', '.join([command.name for command in results])}``"
        ]

        if len(results) != len(retrieved_commands):
            delta = len(retrieved_commands) - len(results)
            if delta == 1:
                embed.set_footer(text=(
                    "1 command has been omitted because you lack the "
                    "permissions required to use it.")
                )
            else:
                embed.set_footer(text=(
                    f"{delta} commands have been omitted because you lack the "
                    "permissions required to use them.")
                )

        embed.description = "\n".join(description)
        return await self.check_and_jumble(embed)

    async def single_help(self, command):
        embed = discord.Embed(title="Help", color=16202876)
        description = [
            f"{self.context.prefix}{command.qualified_name} {command.signature}",
            "<*arg*> represents a required argument. [*arg*] represents an optional argument.",
            "**Do not actually use these brackets when using commands!**\n",
            f"{command.help or '*(No detailed help provided)*'}"
        ]

        if isinstance(command, commands.Group):
            description[0] += "(subcommand)"
            description[1] += " (*subcommand*) represents where a subcommand can be used."
            embed.add_field(
                name=f"{len(command.commands)} subcommand(s):",
                value=f"``{', '.join([c.name for c in command.commands])}``"
            )

        if command.aliases:
            embed.add_field(
                name=f"{len(command.aliases)} alias(es):",
                value=f"``{', '.join(command.aliases)}``"
            )

        cooldown = getattr(command._buckets._cooldown, 'per', None)

        description[0] = f"```{description[0]}```"
        embed.description = "\n".join(description)
        if cooldown:
            embed.set_footer(text=f"This command has a {cooldown} second cooldown.")

        embed = await self.check_and_jumble(embed)
        await self.context.send(embed=embed)

    async def send_command_help(self, command):
        await self.single_help(command)

    async def send_group_help(self, group):
        await self.single_help(group)

    async def send_cog_help(self, cog):
        to_send = await self.generate_cog_help(cog)
        if to_send:
            await self.context.send(embed=to_send)
        else:
            await self.context.send("You do not have the permissions required to use this module.")

    async def send_bot_help(self, _) -> None:
        embed = discord.Embed(title="Help", color=16202876)

        cogs = sorted(self.context.bot.cogs.values(), key=lambda c: c.qualified_name)
        raw_pages = [await self.generate_cog_help(cog) for cog in cogs]
        cog_pages = filter(None, raw_pages)  # type: Iterator[discord.Embed]

        description = [
            "From here, you can:",
            "_ _   • Use the reactions below to navigate between module help pages.",
            "_ _   • Use *<help (module)* to view help on a module.",
            "_ _   • Use *<help (command)* to view help on a command.\n",
            "You can also use *<info* to view more information about Lobstero."
        ]

        embed.description = "\n".join(description)
        embed = await self.check_and_jumble(embed)

        pages = menuclasses.EmbedPageMenu([embed] + list(cog_pages), menuclasses.title_page_number_formatter("Help"))
        menu = menus.MenuPages(pages, timeout=90)
        await menu.start(self.context)

    async def command_not_found(self, string) -> str:
        self.not_found = string  # type: Optional[str]
        return super().command_not_found(string)  # type: str

    async def subcommand_not_found(self, command: commands.Command, string: str):
        r = super().subcommand_not_found(command, string)  # type: str
        if "no subcommands." not in str(r):
            self.not_found = command.qualified_name  # type: Optional[str]

        return r

    async def send_error_message(self, error):
        usable = [c.qualified_name for c in await self.usable_commands(self.context.bot.walk_commands())]
        if not self.not_found:
            command_matches = cog_matches = False
        else:
            usable_cogs = self.context.bot.cogs.keys()  # type: KeysView
            command_matches = difflib.get_close_matches(self.not_found, usable)
            cog_matches = difflib.get_close_matches(self.not_found, usable_cogs)

        if not (command_matches or cog_matches):
            return await self.context.send(error)

        embed = discord.Embed(title=error, color=16202876)
        lines = []
        if cog_matches:
            lines += ["The following modules might be what you're looking for: \n"]
            lines += [f"``{m}``" for m in cog_matches] + ["\n"]
        if command_matches:
            lines += ["Did you mean: \n"]
            lines += [f"``<{m}``" for m in command_matches]

        embed.description = "\n".join(lines)
        await self.context.send(embed=embed)


class Lobstero(commands.AutoShardedBot):

    def __init__(self, *args, config: MutableMapping, **kwargs) -> None:
        self.config = config
        self.session = aiohttp.ClientSession()
        self.logger = logging.getLogger("Lobstero")
        self.first_ready = True
        super().__init__(*args, **kwargs)

    def _unwrapped_markov(self) -> str:
        result = ""
        for _ in range(random.randint(1, 6)):
            result += f"{self._markov_model.make_short_sentence(140)} "

        return result

    async def markov(self, ctx) -> str:
        if self._markov_model is None:
            return "Markov is not configured ."
        else:
            result = f"{await self.loop.run_in_executor(self._pool, self._unwrapped_markov)} "
            result = re.sub("<@(!?)([0-9]*)>", ctx.author.mention, result)
            if ctx.guild:
                result = re.sub("<#([0-9]*)>", lambda _: random.choice(ctx.guild.channels).mention, result)

            result = re.sub(
                "<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>",
                lambda _: str(random.choice(self.emojis)), result
            )

            return result

    async def login(self, *args, **kwargs):
        # we override this and use it as an async pre-ready hook
        # in this case, we're connecting to the DB now so that it's usable immediately upon ready
        try:
            self.db = await bigbeans.connect(
                host=self.config["database"]["server"],
                port=self.config["database"]["port"],
                database=self.config["database"]["database_name"],
                user=self.config["database"]["username"],
                password=self.config["database"]["password"]
            )
        except Exception as error:
            self.logger.critical("Connection to database failed: %s", str(error))
        else:
            self.logger.info("Connection to database established.")

        for cog in self.cogs.values():
            func = getattr(cog, "before_ready", None)
            if func:
                try:
                    await func()
                except Exception as error:
                    self.logger.critical("Error while trying to ready cog %s: %s", cog.qualified_name, str(error))
                else:
                    self.logger.info("Cog %s is ready!", cog.qualified_name)
            else:
                self.logger.info("Cog %s has no before_ready function, skipping.", cog.qualified_name)

        # normal login
        await super().login(*args, **kwargs)

    async def get_context(self, message, *, cls=CustomContext) -> CustomContext:
        return await super().get_context(message, cls=cls)

    async def on_ready(self):
        self.logger.info("Connection to discord established.")

    async def on_message(self, message):
        # implement channel blocking here; until then
        if message.author.bot:
            return

        ctx = await self.get_context(message)
        if f"<@{self.user.id}>" in message.content or f"<@!{self.user.id}>" in message.content:
            try:
                await message.channel.send(await self.markov(ctx))
            except discord.Forbidden:
                pass  # too bad

        await self.invoke(ctx)

    async def on_command_error(self, ctx, error):
        error = getattr(error, "original", error)  # just in case bb

        if isinstance(error, (commands.CommandNotFound, discord.Forbidden)):
            return

        self.logger.warning(
            "Guild %s (ID %s) Author %s (ID %s) Channel %s (ID %s)\n%s",
            str(ctx.guild), str(ctx.guild.id) if ctx.guild else "N/A", str(ctx.author), str(ctx.author.id),
            str(ctx.channel), str(ctx.channel.id) if ctx.channel else "N/A",
            "".join(traceback.format_exception(type(error), error, error.__traceback__, 4))
        )

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                "Missing argument \"{0}\" - try ``{1}help {2}``?".format(
                    error.param.name, ctx.prefix, ctx.command.qualified_name
                ), delete_after=10
            )

        if isinstance(error, commands.BadArgument):
            await ctx.send(
                "Bad command usage - try ``{0}help {1}``?".format(
                    ctx.prefix, ctx.command.qualified_name
                ), delete_after=10
            )

        if isinstance(error, commands.BadArgument):
            await ctx.send(
                "Too many arguments - try ``{0}help {1}``?".format(
                    ctx.prefix, ctx.command.qualified_name
                ), delete_after=10
            )

        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send(
                "I am missing permissions:\n{0}".format(
                    "``" + "``, ``".join(error.missing_perms) + "``"
                ), delete_after=10
            )

        if isinstance(error, commands.MissingPermissions):
            await ctx.send(
                "You are missing permissions:\n{0}".format(
                    "``" + "``, ``".join(error.missing_perms) + "``"
                ), delete_after=10
            )

        if isinstance(error, commands.NotOwner):
            await ctx.send(
                "<a:dread_alarm:670546197060124673> not owner! <a:dread_alarm:670546197060124673>",
                delete_after=10
            )

        if isinstance(error, commands.DisabledCommand):
            await ctx.send(
                "<a:dread_alarm:670546197060124673> Command disabled! <a:dread_alarm:670546197060124673>",
                delete_after=10
            )

        if isinstance(error, commands.MaxConcurrencyReached):
            await ctx.send("Command already in use!", delete_after=10)

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send("Command on cooldown - try again in {:.2f}s.".format(error.retry_after), delete_after=10)

        if isinstance(error, OverflowError):
            await ctx.send("**``Reconsider``**", delete_after=10)

        if isinstance(error, exceptions.OnExtendedCooldown):
            await ctx.send("⏰ You're on cooldown! You can do this again {}!".format(str(error)), delete_after=10)
