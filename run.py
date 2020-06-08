import os

from concurrent.futures import ThreadPoolExecutor

import pendulum
import click
import toml
import markovify

from extensions.models import botclasses
from discord.ext import commands

INITIAL_EXTENSIONS = [
    "extensions.admin",
    "extensions.database",
    "extensions.images",
    "extensions.bottogames",
    "extensions.currency"
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

    bot._start_time = pendulum.now()
    if config["advanced"]["override_max_workers"]:
        bot._pool = ThreadPoolExecutor(max_workers=config["advanced"]["max_workers"])
    else:
        bot._pool = ThreadPoolExecutor(max_workers=10)

    for extension in INITIAL_EXTENSIONS:
        try:
            bot.load_extension(extension)
        except commands.ExtensionAlreadyLoaded:
            bot.logger.info("Extension %s already loaded, skipping.", extension)
        # except Exception as error:
        #     bot.logger.critical("Could not load extension %s: %s", extension, str(error))
        else:
            bot.logger.info("Extension %s loaded successfully.", extension)

    if config["markov"]["use_markov"]:
        # check if we have a frozen model available
        if os.path.isfile(config["markov"]["filepath"] + ".generated"):
            bot.logger.info("Pre-generated model found! Loading...")
            with open(config["markov"]["filepath"] + ".generated", "r", encoding="utf-8", errors="ignore") as f:
                bot._markov_model = markovify.NewlineText.from_json(f.read())

            bot.logger.info("Model loaded.")
        else:
            # no frozen model, generate
            bot.logger.info("Generating markov model! This may take a while.")
            with open(config["markov"]["filepath"], "r", encoding="utf-8", errors="ignore") as f:
                bot._markov_model = markovify.NewlineText(f, retain_original=False, state_size=2)

            bot._markov_model.compile(inplace=True)
            bot.logger.info("Model generated.")
            with open(config["markov"]["filepath"] + ".generated", "w+", encoding="utf-8", errors="ignore") as f:
                f.write(bot._markov_model.to_json())

            bot.logger.info("Saved generated model for future usage.")
    else:
        bot._markov_model = None

    bot.run(token)


run()
