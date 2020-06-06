# Lobstero Redux
 A refocused and improved version of the lobstero discord bot.
 It sucks slightly less now.

### Setup and usage
 Getting the bot up and running is quite easy. I recommend that you use a venv or an otherwise isolated python environment.
 Do note that python snippets will depend on your environment.
 1. Install dependencies from requirements.txt. This is `python -m pip install -r requirements.txt`, or your favorite variant thereof.
    + You will need the pillow library. It is intentionally left out of requirements.txt because you can install Pillow-SIMD (https://github.com/uploadcare/Pillow-SIMD) as a drop-in replacement for performance improvements.
    + However, if it was that simple, Pillow-SIMD would be in requirements.txt already - it comes with the caveat of being annoying to compile & install in some environments. Choose which is easier for you.
 2. Get a PostgreSQL database set up. I've only tested PostgreSQL 12 and up, but theoretically anything newer than version 9.5 should work fine.
 3. Copy config.example.toml, rename it to config.toml, and fill it out in your favorite text editor.
    + Any API keys that you might need are explained in the example config file.
    + If you choose to run a Lobstero API instance, you will want the configured groups to be "cursedcats" and "gnomes" - feel free to put whatever files you'd like in there.
 4. Run `python run.py` to run the bot in debug mode, or `python run.py --production` to run the bot in production mode.
    + To see additional CLI options, use `python run.py --help`.