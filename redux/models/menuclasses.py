from discord.ext import menus


class HelpMenu(menus.ListPageSource):
    """A simple menu for the help command."""
    def __init__(self, data):
        super().__init__(data, per_page=1)
        self.data_len = len(data)

    async def format_page(self, menu, entries):
        entries.title = f"Help (page {menu.current_page + 1}/{self.data_len})"

        return entries
