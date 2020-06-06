import click
import toml

from redux.models import botclasses


@click.command()
@click.option("--debug", is_flag=True, type=bool, help="Runs the bot in debug mode (True or False)")
@click.option("--config", is_flag=True, type=click.Path(exists=True), help="Uses an alternate path for configuration.")
def run(**kwargs):
    try:
        with open(kwargs.get("config", None) or "config.toml", "r") as tomlfile:
            config = toml.load(tomlfile)
    except FileNotFoundError:
        print("Configuration file not found!")
        exit()

    token = config["token"]["debug"] if kwargs.get("debug", None) else config["token"]["production"]
    bot = botclasses.Lobstero(
        command_prefix=...,
        help_command=botclasses.CustomHelpCommand,
        description="A discord bot for having fun.",
        case_insensitive=True
    )

    bot.run(token)


if __name__ == "__main__":
    run()