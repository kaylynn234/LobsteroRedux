import click
import toml

from extensions.models import botclasses
from discord.ext import commands

INITIAL_EXTENSIONS = [
    "jishaku",
    "extensions.database",
    "extensions.images",
    "extensions.bottogames"
]


@click.command()
@click.option("--production", is_flag=True, type=bool, help="Runs the bot in production mode.")
@click.option("--config", type=click.Path(exists=True), help="Uses an alternate path for configuration.")
def run(**kwargs):
    try:
        with open(kwargs.get("config", None) or "config.toml", "r") as tomlfile:
            config = toml.load(tomlfile)
    except FileNotFoundError:
        print("Configuration file not found!")
        exit()

    token = config["token"]["production"] if kwargs.get("production", None) else config["token"]["debug"]
    bot = botclasses.Lobstero(
        config=config,
        command_prefix=config["config"]["default_prefix"],
        help_command=botclasses.CustomHelpCommand(),
        description="A discord bot for having fun.",
        case_insensitive=True
    )

    for extension in INITIAL_EXTENSIONS:
        try:
            bot.load_extension(extension)
        except commands.ExtensionAlreadyLoaded:
            bot.logger.info("Extension %s already loaded, skipping.", extension)
        # except Exception as error:
        #     bot.logger.critical("Could not load extension %s: %s", extension, str(error))
        else:
            bot.logger.info("Extension %s loaded successfully.", extension)

    bot.run(token)


run()
