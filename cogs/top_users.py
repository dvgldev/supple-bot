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

DATABASE_URL = "sqlite:///testbot.db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

Base.metadata.create_all(engine)

class ActivityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot_messages_id = 1236274638980649113

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        session = Session()
        user = session.query(UserActivity).filter_by(user_id=str(message.author.id)).first()
        if not user:
            user = UserActivity(user_id=str(message.author.id), username=str(message.author.display_name), text_messages=0, voice_minutes=0.0)
            session.add(user)
        
        user.text_messages = (user.text_messages or 0) + 1
        session.commit()
        session.close()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        session = Session()
        user = session.query(UserActivity).filter_by(user_id=str(member.id)).first()
        if not user:
            user = UserActivity(user_id=str(member.id), username=str(member.display_name), text_messages=0, voice_minutes=0.0)
            session.add(user)
        
        if before.channel is None and after.channel is not None:
            user.voice_join_time = datetime.datetime.utcnow()
        elif before.channel is not None and after.channel is None:
            if user.voice_join_time:
                join_time = user.voice_join_time
                leave_time = datetime.datetime.utcnow()
                minutes_in_channel = (leave_time - join_time).total_seconds() / 60
                user.voice_minutes = (user.voice_minutes or 0) + minutes_in_channel
                user.voice_join_time = None
        
        user.username = str(member.display_name)
        session.commit()
        session.close()

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        session = Session()
        user = session.query(UserActivity).filter_by(user_id=str(member.id)).first()
        if user:
            session.delete(user)
            session.commit()
        session.close()

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.display_name != after.display_name:
            session = Session()
            user = session.query(UserActivity).filter_by(user_id=str(after.id)).first()
            if user:
                user.username = str(after.display_name)
                session.commit()
            session.close()

    @commands.slash_command(name="top", description="Показати найактивніших користувачів.")
    async def top(self, inter, amount: int, type: str = commands.Param(choices=["voice_online", "text_online"])):
        session = Session()
        
        if type == "voice_online":
            users = session.query(UserActivity).order_by(UserActivity.voice_minutes.desc()).limit(amount).all()
        elif type == "text_online":
            users = session.query(UserActivity).order_by(UserActivity.text_messages.desc()).limit(amount).all()
        else:
            await inter.response.send_message("**❌ Помилка**: Невідомий тип активності.", ephemeral=True)
            return
        
        if not users:
            await inter.response.send_message("**❌ Помилка**: Немає даних про активність користувачів.", ephemeral=True)
            return

        guild = inter.guild
        embed = disnake.Embed(title="🏆 Топ найактивніших користувачів на сервері:", color=disnake.Color.gold())
        
        for i, user in enumerate(users, 1):
            member = guild.get_member(int(user.user_id))
            if member:
                if type == "voice_online":
                    hours, remainder = divmod(user.voice_minutes * 60, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    embed.add_field(name=" ", value=" ", inline=False)
                    embed.add_field(
                        name=f"**{i}.** {member.display_name}",
                        value=f"> **Онлайн у войс-чатах:** `{int(hours)}г {int(minutes)}хв {int(seconds)}с`\n> **Кіль-сть повідомлень у чаті:** `{user.text_messages}`",
                        inline=False
                    )
                elif type == "text_online":
                    hours, remainder = divmod(user.voice_minutes * 60, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    embed.add_field(name=" ", value=" ", inline=False)
                    embed.add_field(
                        name=f"**{i}.** {member.display_name}",
                        value=f"> **Кіль-сть повідомлень у чаті:** `{user.text_messages}`\n> **Онлайн у войс-чатах:** `{int(hours)}г {int(minutes)}хв {int(seconds)}с`",
                        inline=False
                    )

        channel = self.bot.get_channel(self.bot_messages_id)
        await channel.send(embed=embed)
        await inter.response.send_message(f"✨ **Команда успішно застосована!** Результат можна подивитися в каналі <#{self.bot_messages_id}>.", ephemeral=True)


def setup(bot):
    print("Loading Activity cog...")
    bot.add_cog(ActivityCog(bot))