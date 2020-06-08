import inspect

import discord

from discord.ext import menus


# these can use a base class or something similar, will implement later
class EmbedPageMenu(menus.ListPageSource):
    """A simple abstract menu class.
    If the formatter parameter is given, the provided function will be used to format data.
    The function should take the parameters embed, pages, and menu.
    It should return a new embed to be displayed, or None to use the original
    This function must not be a coroutine."""

    def __init__(self, data, formatter=None):
        super().__init__(data, per_page=1)
        self.data_len = len(data)
        if formatter is not None:
            if inspect.isfunction(formatter):
                self.formatter = formatter
            else:
                raise TypeError(f"Formatter parameter must be a function, not object of type {type(formatter)}")
        else:
            self.formatter = None

    async def format_page(self, menu, entries: discord.Embed):
        if self.formatter:
            adjusted = self.formatter(entries, self, menu)
            return adjusted or entries

        return entries


class ListPageMenu(menus.ListPageSource):
    """A simple menu class for paginating sequences.
    If the formatter parameter is given, the provided function will be used to format data.
    The function should take the parameters embed, pages, and menu.
    It should return a new embed to be displayed, or None to use the original
    This function must not be a coroutine."""

    def __init__(self, data, per_page: int = 10, formatter=None):
        super().__init__(data, per_page=per_page)
        self.data_len = len(data)
        if formatter is not None:
            if inspect.isfunction(formatter):
                self.formatter = formatter
            else:
                raise TypeError(f"Formatter parameter must be a function, not object of type {type(formatter)}")
        else:
            self.formatter = None

    async def format_page(self, menu, entries):
        embed = discord.Embed(
            color=16202876,
            description="\n".join(entries))

        if self.formatter:
            adjusted = self.formatter(embed, self, menu)
            return adjusted or embed

        return embed


def title_page_number_formatter(title):

    def formatter(embed, pages, menu):
        per = pages.data_len / pages.per_page
        actual_page_count = int(per) + 1 if pages.data_len % pages.per_page else int(per)
        embed.title = f"{title} (page {menu.current_page + 1}/{actual_page_count})"
        return embed

    return formatter
