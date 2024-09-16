import disnake
from disnake.ext import commands
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

Base = declarative_base()

class UserActivity(Base):
    __tablename__ = 'user_activity'
    id = Column(Integer, primary_key=True)
    user_id = Column(String, unique=True)
    username = Column(String)
    voice_minutes = Column(Float, default=0.0)
    text_messages = Column(Integer, default=0)
    voice_join_time = Column(DateTime, default=None)
    exp = Column(Integer, default=0)

DATABASE_URL = "sqlite:///testbot.db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

Base.metadata.create_all(engine)

class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot_messages_id = 1236274638980649113

    @commands.slash_command(name="stats", description="Показати статистику користувача.")
    async def stats(self, inter, member: disnake.Member):
        session = Session()
        user = session.query(UserActivity).filter_by(user_id=str(member.id)).first()
        
        if not user:
            await inter.response.send_message("**❌ Помилка**: Немає даних про активність користувача.", ephemeral=True)
            session.close()
            return

        guild_member = inter.guild.get_member(int(user.user_id))
        if not guild_member:
            await inter.response.send_message("**❌ Помилка**: Користувач не знайдений на сервері.", ephemeral=True)
            session.close()
            return

        join_date = guild_member.joined_at.strftime("%Y-%m-%d %H:%M:%S") if guild_member.joined_at else "Невідомо"
        hours, remainder = divmod(user.voice_minutes * 60, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        exp = int(user.exp)

        embed = disnake.Embed(title=f"🔎 Статистика користувача {guild_member.display_name}", color=0x007FFF)
        embed.add_field(name="Нікнейм:", value=f"{member.mention}", inline=False)
        embed.add_field(name="Дата приєднання до серверу:", value=f"`{join_date}`", inline=False)
        embed.add_field(name="Онлайн у войс-чатах:", value=f"`{int(hours)}г {int(minutes)}хв {int(seconds)}с`", inline=False)
        embed.add_field(name="Кіль-сть повідомлень у чаті:", value=f"`{user.text_messages}`", inline=False)
        embed.add_field(name="Кіль-сть EXP:", value=f"`{str(exp)}`", inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)

        channel = self.bot.get_channel(self.bot_messages_id)
        await channel.send(embed=embed)
        await inter.response.send_message(f"✨ **Команда успішно застосована!** Результат можна подивитися в каналі <#{self.bot_messages_id}>", ephemeral=True)
        session.close()


def setup(bot):
    print("Loading Stats cog...")
    bot.add_cog(StatsCog(bot))