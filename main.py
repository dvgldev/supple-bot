import disnake
from disnake.ext import commands
import sqlite3
import os


bot = commands.InteractionBot(intents=disnake.Intents.all())

conn = sqlite3.connect('testbot.db')
cursor = conn.cursor()

conn.commit()
conn.close()


@bot.event
async def on_ready():
    print("Bot is ready to work!")


@bot.event
async def on_member_join(member):
    channel = member.guild.system_channel
    rules_channel_id = 1238792843154296892
    rules_channel = member.guild.get_channel(rules_channel_id)
    embed = disnake.Embed(
        title="",
        description=f"**🎉 Вітаємо**, {member.mention}.\n\n**Ми раді, що Ви тут!**\nРекомендуємо Вам ознайомитись з правилами серверу у каналі {rules_channel.mention} та списком доступних команд за допомогою команди `/help`.",
        color=0x007FFF
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    await channel.send(embed=embed)


for file in os.listdir("cogs"):
    if file.endswith(".py"):
        bot.load_extension(f"cogs.{file[:-3]}")


bot.run("MTIzNDg5ODM1NzkzMjAwMzQ3MA.GrDiAS.edMWAdPvnUAZQRaEnxcxtQY9b8QR4lPBNzCpmA")