import disnake
from disnake.ext import commands


class News(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="news", description="Створити новину.")
    async def news(self, ctx, title, *, message):
        if ctx.channel.id != 1239897260054282261:
            await ctx.send("**❌ Помилка:** Цю команду можна використати лише в каналі <#1239897260054282261> або Ви не маєте доступу до її використання.", ephemeral=True)
            return
        
        if not disnake.utils.get(ctx.author.roles, id=1239181262753890305):
            await ctx.send("**❌ Помилка:** Цю команду можна використати лише в каналі <#1239897260054282261> або Ви не маєте доступу до її використання.", ephemeral=True)
            return

        embed = disnake.Embed(title=title, description=message, color=0x007FFF)
        embed.set_footer(text='З повагою, команда TEST SERVER 🤍', icon_url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)


def setup(bot):
    print("Loading News cog...")
    bot.add_cog(News(bot))
