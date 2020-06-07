import random
import asyncio

import discord

from discord.ext import menus, commands
from typing import Optional, Sequence


EMOJI_DIRECTION_MAPPING = {
    "⬅": "left",
    "➡": "right",
    "⬆": "up",
    "⬇": "down"
}


OFFSET_MAPPING = {
    "left": [-1, 0],
    "right": [1, 0],
    "up": [0, -1],
    "down": [0, 1],
}


class maize_array():

    def __init__(self, w=11, h=7):
        self.width, self.height = w, h
        self.generate_maze()

    def clamp(self, x, minimum, maximum):
        return max(minimum, min(x, maximum))

    def get_point(self, x, y):
        return self.list[self.clamp(y, 0, self.height - 1)][self.clamp(x, 0, self.width - 1)][0]

    def set_point(self, x, y, val):
        self.list[self.clamp(y, 0, self.height - 1)][self.clamp(x, 0, self.width - 1)][0] = val

    def botto_pos(self) -> Optional[Sequence[int]]:
        for y_index, y in enumerate(self.list):
            for x_index, x in enumerate(y):
                if self.list[y_index][x_index][0] == "<:maize_botto:646810169556336650>":
                    return [x_index, y_index]

        return None

    def join(self):
        e = "🌽"

        s = "".join([e for _ in range(self.width + 2)]) + "\n"
        for row in self.list:
            s += "".join([f"{e}", "".join([f"{item[0]}" for item in row]), f"{e} \n"])

        s += "".join([e for _ in range(self.width + 2)])

        return s.replace("None", "⬛")

    def generate_maze(self):

        corn = "🌽"
        death = "<:maize_death:646810168897568770>"
        end = "<:maize_end:646810352067018762>"
        botto = "<:maize_botto:646810169556336650>"
        nothing = "⬛"

        self.list = [
            [[None], [None], [None], [None], [None], [None], [None], [None], [None], [None], [None]],
            [[None], [None], [None], [None], [None], [None], [None], [None], [None], [None], [None]],
            [[None], [None], [None], [None], [None], [None], [None], [None], [None], [None], [None]],
            [[None], [None], [None], [None], [None], [None], [None], [None], [None], [None], [None]],
            [[None], [None], [None], [None], [None], [None], [None], [None], [None], [None], [None]],
            [[None], [None], [None], [None], [None], [None], [None], [None], [None], [None], [None]],
            [[None], [None], [None], [None], [None], [None], [None], [None], [None], [None], [None]]
        ]

        def generate_random_direction():
            generated = [0, random.choice([-1, 1])]
            return random.shuffle(generated) or generated

        def is_valid(xpos, ypos):
            if self.get_point(xpos, ypos) == nothing:
                v = [
                    [(self.get_point(xpos + 1, ypos) is None), [xpos + 1, ypos]],
                    [(self.get_point(xpos - 1, ypos) is None), [xpos - 1, ypos]],
                    [(self.get_point(xpos, ypos + 1) is None), [xpos, ypos + 1]],
                    [(self.get_point(xpos, ypos - 1) is None), [xpos, ypos - 1]]
                ]

                for i in v:
                    if i[0] is True:
                        return i

                return (False, [0, 0])

            else:
                return (False, [0, 0])

        self.path_x = random.randint(1, self.width)
        self.path_y = random.randint(1, self.height)
        self.dir = generate_random_direction()

        for _ in range(random.randint(self.width * 5, self.width * 6)):
            if random.randint(1, 4) == 4:
                self.dir = generate_random_direction()

            if self.get_point(self.path_x + self.dir[0], self.path_y + self.dir[1]) is None:
                self.set_point(self.path_x + self.dir[0], self.path_y + self.dir[1], nothing)
                self.path_x, self.path_y = self.path_x + self.dir[0], self.path_y + self.dir[1]
            else:
                self.dir = generate_random_direction()

        valid_locations = []

        for y_index, y in enumerate(self.list):
            for x_index, x in enumerate(y):
                valid = is_valid(x_index, y_index)
                if valid[0]:
                    valid_locations.append(valid[1])

        def random_pop(l):
            return l.index(random.choice(l))

        end_pos = valid_locations.pop(random_pop(valid_locations))
        death_pos = valid_locations.pop(random_pop(valid_locations))
        botto_pos = valid_locations.pop(random_pop(valid_locations))

        self.set_point(end_pos[0], end_pos[1], end)
        self.set_point(death_pos[0], death_pos[1], death)
        self.set_point(botto_pos[0], botto_pos[1], botto)

        for y_index, y in enumerate(self.list):
            for x_index, x in enumerate(y):
                if x == [None]:
                    self.set_point(x_index, y_index, corn)


class MaizeGame(menus.Menu):
    """The class that maize maze is run with."""

    def __init__(self):
        """Does the things."""
        super().__init__(timeout=30, clear_reactions_after=True)
        self.maze = maize_array()
        self.tries = 3
        self.movements = 0
        # Create the buttons from the abstraction and add relevant information
        for button_emoji in EMOJI_DIRECTION_MAPPING.keys():
            b = menus.Button(button_emoji, self.abstract_process_direction)
            self.add_button(b)

    def format_description(self, title="A game of Maize Maze has begun!", footer=None, preserve_instructions=True, preserve_maze=True):
        """Formats the embed description properly."""

        m = f"**{title}** "
        if preserve_instructions:
            m += "Use the ⬅ ⬆ ➡ ⬇ reactions below to move botto. Use the ⏹️ reaction to quit. Good luck!"
        if preserve_maze:
            m += f"\n\n{self.maze.join()}"
        if footer:
            m += f"\n\n{footer}"

        return m

    async def send_initial_message(self, ctx, channel):
        """Sends the message that becomes the host for a maize maze game"""
        mazebed = discord.Embed(title="Maize maze!", description=self.format_description(), color=16202876)
        return await ctx.send(embed=mazebed)

    @menus.button("\N{BLACK SQUARE FOR STOP}\ufe0f")
    async def on_stop(self, _):
        """Stops the game."""
        mazetext = self.format_description("Botto is dead and you are entirely responsible.", "Know this. Feel guilt. It was your unwilling that killed him.", False, False)
        mazebed = discord.Embed(title="Maize maze!", description=mazetext, color=16202876)
        await self.message.edit(embed=mazebed)

        self.stop()
        del self

    async def process_total_movements(self):
        """Makes sure the maize gods aren't too far behind."""
        self.movements += 1

        if self.movements > 20:
            mazetext = self.format_description(
                "Botto is dead and you are entirely responsible.",
                "The Maize Gods were not far away, and you were not fast enough. The end has come.",
                False, False
            )

            mazebed = discord.Embed(title="Maize maze!", description=mazetext, color=16202876)
            await self.message.edit(embed=mazebed)

            return False
        return True

    async def process_direction(self, direction):
        """Processes where botto goes."""
        botto_x, botto_y = self.maze.botto_pos()
        offset = OFFSET_MAPPING[direction]
        tile = self.maze.get_point(botto_x + offset[0], botto_y + offset[1]) or "⬛"

        if "botto" in str(tile) or "🌽" in str(tile):
            self.tries -= 1

            if self.tries > 0:
                mazetext = self.format_description(
                    "Botto cannot move there!",
                    (f"Botto has {self.tries} flesh remaining before the Maize Gods reach him.")
                )

                mazebed = discord.Embed(title="Maize maze!", description=mazetext, color=16202876)
                await self.message.edit(embed=mazebed)
            else:
                mazetext = self.format_description(
                    "Botto is dead and you are entirely responsible.",
                    "His body was found covered in ears of maize. Cause of death? Slaughter.",
                    False, False
                )

                mazebed = discord.Embed(title="Maize maze!", description=mazetext, color=16202876)
                await self.message.edit(embed=mazebed)
                self.stop()
                del self

        elif any(("⬛" in str(tile), "end" in str(tile), "death" in str(tile))):
            self.maze.set_point(botto_x, botto_y, "⬛")
            self.maze.set_point(botto_x + offset[0], botto_y + offset[1], "<:maize_botto:646810169556336650>")
            mazebed = discord.Embed(
                title="Maize maze!",
                description=self.format_description("The game of Maize Maze continues."), color=16202876)

            await self.message.edit(embed=mazebed)

            if "deat" in str(tile):
                await asyncio.sleep(2)

                mazetext = self.format_description(
                    "Botto is dead and you are entirely responsible.",
                    "Sit with this truth and weep.",
                    False, False
                )

                mazebed = discord.Embed(title="Maize maze!", description=mazetext, color=16202876)
                await self.message.edit(embed=mazebed)
                self.stop()
                del self

            elif "end" in str(tile):
                await asyncio.sleep(2)

                mazetext = self.format_description(
                    "Botto has been saved from the Maize Gods!",
                    "You win!\n\n(Saved from the Maize Gods for a little while, at least.)",
                    False, False
                )

                mazebed = discord.Embed(title="Maize maze!", description=mazetext, color=16202876)
                await self.message.edit(embed=mazebed)
                self.stop()
                del self

            elif "⬛" not in str(tile):
                await self.message.edit(content=(
                    "Congratulations, you found the unfindable embed!"
                    "Now time wil collapse. \n\n(This shouldn't be possible. Tell Kaylynn.)")
                )

    async def abstract_process_direction(self, payload):
        """An abstract function that is fed to a button for processing movement."""
        if await self.process_total_movements():
            await self.process_direction(EMOJI_DIRECTION_MAPPING[payload.emoji.name])
        else:
            self.stop()
            del self


class BottoGames(commands.Cog, name="Botto Games"):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.max_concurrency(1, commands.BucketType.channel)
    @commands.cooldown(4, 60, commands.BucketType.user)
    async def maizemaze(self, ctx):
        """Help Botto navigate through a treacherous maze of corn and horror."""

        await MaizeGame().start(ctx)


def setup(bot):
    bot.add_cog(BottoGames(bot))
