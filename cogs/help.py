import disnake
from disnake.ext import commands

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="help", description="Показати список команд на сервері.")
    async def help(self, inter: disnake.ApplicationCommandInteraction):
        title = "📃 Список серверних команд"
        user_commands = ("**/help** - показати список команд;\n"
                        "**/stats** `{користувач}` - показати статистику користувача;\n"
                        "**/top** `{кількість}` `{категорія}` - показати топ-користувачів за активністю у войсах та чатах;\n"
                        "**/pay** `{користувач}` `{кількість}` - передати T-COINS іншому користувачу;\n"
                        "**/coin** `{кількість}` - Гра 'Орел або решка' на T-COINS;\n"
                        "**/daily** - отримати тимчасову винагороду в T-COINS;\n"
                        "**/balance** - подивитися актуальний баланс;\n"
                        "**/transactions** - подивитися останні п'ять транзакцій.")
        mod_commands = ("**/kick** `{користувач}` `{причина}` - вигнати користувача з сервера;\n"
                        "**/ban** `{користувач}` `{причина}` - заблокувати користувача на сервері;\n"
                        "**/mute** `{користувач}` `{хвилини}` `{причина}` - замовкнути користувача на сервері;\n"
                        "**/give_coin** `{користувач}` `{кількість}` - видати T-COINS користувачу;\n"
                        "**/take_coin** `{користувач}` `{кількість}` - забрати T-COINS у користувача;\n"
                        "**/give_exp** `{користувач}` `{кількість}` - видати EXP користувачу;\n"
                        "**/take_exp** `{користувач}` `{кількість}` - забрати EXP у користувача;\n"
                        "**/news** `{повідомлення}` - створити новину;\n"
                        "**/clear** `{кількість}` - очистити чат;\n"
                        "**/create_lottery** - створити лотерею.")
        event_commands = ("**/create_event** `{template_id}` `{date_time}` - створити івент.")
        
        embed = disnake.Embed(title=title, color=0x007FFF)
        embed.add_field(name="`Основні команди  \t\t\t\t\t\t\t\t\t\t\t\t\t`", value=user_commands, inline=False)
        embed.add_field(name="\u2004", value="\u2004", inline=False)
        embed.add_field(name="`Команди модерації\t\t\t\t\t\t\t\t\t\t\t\t\t`", value=mod_commands, inline=False)
        embed.add_field(name="\u2004", value="\u2004", inline=False)
        embed.add_field(name="`Команди івенторів\t\t\t\t\t\t\t\t\t\t\t\t\t`", value=event_commands, inline=False)
        
        await inter.response.send_message(embed=embed, ephemeral=True)


def setup(bot):
    print("Loading Help cog...")
    bot.add_cog(Help(bot))
