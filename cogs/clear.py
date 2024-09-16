import disnake
from disnake.ext import commands

MAX_MESSAGES_TO_DELETE = 20

class Clear(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="clear", description="Видалення вказаної кількості повідомлень у чаті.")
    async def clear(self, inter, amount: int):
        if amount <= 0 or amount > MAX_MESSAGES_TO_DELETE:
            embed = disnake.Embed(
                description=f"Кількість повідомлень, яку ви хочете видалити, повинна бути **не менше 1-го і не більше {MAX_MESSAGES_TO_DELETE}**.",
                color=disnake.Color.red()
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        await inter.response.defer()

        await inter.channel.purge(limit=amount + 1)


def setup(bot):
    print("Loading Clear cog...")
    bot.add_cog(Clear(bot))