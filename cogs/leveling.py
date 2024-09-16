import disnake
from disnake.ext import commands
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import asyncio

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

INITIAL_ROLE_ID = 1238205020302741555
ROLE_THRESHOLDS = [
    (250, 1254806696283344980),
    (750, 1254807250850156636),
    (1250, 1254807368512831488),
    (2000, 1254807528752156712),
    (4000, 1254807845405327500),
]
ADMIN_ROLE_ID = 1239181262753890305
NOTIFICATION_CHANNEL_ID = 1236274638980649113

class LevelingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def update_user_exp(self, user, session, message_exp=0, voice_exp=0, exp_change=0):
        user.exp = (user.exp or 0) + message_exp + voice_exp + exp_change
        session.commit()

    async def update_user_roles(self, member, new_exp):
        current_roles = {role.id for role in member.roles}
        new_role = INITIAL_ROLE_ID

        for exp_threshold, role_id in ROLE_THRESHOLDS:
            if new_exp >= exp_threshold:
                new_role = role_id
            else:
                break
        
        if new_role not in current_roles:
            roles_to_remove = {INITIAL_ROLE_ID} | {role_id for _, role_id in ROLE_THRESHOLDS}
            await member.remove_roles(*[disnake.Object(role_id) for role_id in roles_to_remove if role_id in current_roles])
            await member.add_roles(disnake.Object(new_role))

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        session = Session()
        user = session.query(UserActivity).filter_by(user_id=str(message.author.id)).first()
        if not user:
            user = UserActivity(user_id=str(message.author.id), username=str(message.author.display_name))
            session.add(user)
            session.commit()
        
        self.update_user_exp(user, session, message_exp=1)
        await self.update_user_roles(message.author, user.exp)
        session.close()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        session = Session()
        user = session.query(UserActivity).filter_by(user_id=str(member.id)).first()
        if not user:
            user = UserActivity(user_id=str(member.id), username=str(member.display_name))
            session.add(user)
            session.commit()

        if before.channel is None and after.channel is not None:
            user.voice_join_time = datetime.datetime.utcnow()
        elif before.channel is not None and after.channel is None:
            if user.voice_join_time:
                join_time = user.voice_join_time
                leave_time = datetime.datetime.utcnow()
                minutes_in_channel = (leave_time - join_time).total_seconds() / 60
                user.voice_minutes = (user.voice_minutes or 0) + minutes_in_channel
                voice_exp = (minutes_in_channel / 60) * 10
                self.update_user_exp(user, session, voice_exp=voice_exp)
                user.voice_join_time = None
        
        user.username = str(member.display_name)
        await self.update_user_roles(member, user.exp)
        session.commit()
        session.close()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await member.add_roles(disnake.Object(INITIAL_ROLE_ID))


class ExpManagementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_slash_command_check(self, inter):
        if not any(role.id == ADMIN_ROLE_ID for role in inter.author.roles):
            await inter.response.send_message("**❌ Помилка:** Ви не маєте доступу до використання цієї команди.", ephemeral=True)
            return False
        return True

    @commands.slash_command(name="give_exp", description="Видати EXP користувачу.")
    async def give_exp(self, inter, member: disnake.Member, exp: int):
        session = Session()
        user = session.query(UserActivity).filter_by(user_id=str(member.id)).first()
        if not user:
            user = UserActivity(user_id=str(member.id), username=str(member.display_name))
            session.add(user)
            session.commit()

        LevelingCog(self.bot).update_user_exp(user, session, exp_change=exp)
        await LevelingCog(self.bot).update_user_roles(member, user.exp)

        author_display_name = inter.author.display_name

        session.close()

        await inter.response.send_message(f":coin: Ви успішно видали **{exp}** EXP користувачу **{member.display_name}**.", ephemeral=True)
        await asyncio.sleep(3)

        channel = self.bot.get_channel(NOTIFICATION_CHANNEL_ID)
        embed = disnake.Embed(
            title=" ",
            description=f":inbox_tray: Модератор {inter.author.mention} видав користувачу {member.mention} **{exp}** EXP.",
            color=disnake.Color.green()
        )
        await channel.send(embed=embed)
        print(f"Модератор {author_display_name} видав користувачу {member.display_name} {exp} EXP.")


    @commands.slash_command(name="take_exp", description="Забрати EXP у користувача.")
    async def take_exp(self, inter, member: disnake.Member, exp: int):
        session = Session()
        user = session.query(UserActivity).filter_by(user_id=str(member.id)).first()
        if not user:
            user = UserActivity(user_id=str(member.id), username=str(member.display_name))
            session.add(user)
            session.commit()

        LevelingCog(self.bot).update_user_exp(user, session, exp_change=-exp)
        await LevelingCog(self.bot).update_user_roles(member, user.exp)

        author_display_name = inter.author.display_name

        session.close()

        await inter.response.send_message(f"💔 Ви успішно забрали **{exp}** EXP у користувача **{member.display_name}**.", ephemeral=True)
        await asyncio.sleep(3)

        channel = self.bot.get_channel(NOTIFICATION_CHANNEL_ID)
        embed = disnake.Embed(
            title=" ",
            description=f":outbox_tray: Модератор {inter.author.mention} забрав у користувача {member.mention} **{exp}** EXP.",
            color=disnake.Color.red()
        )
        await channel.send(embed=embed)
        print(f"Модератор {author_display_name} забрав у користувача {member.display_name} {exp} EXP.")


def setup(bot):
    print("Loading Leveling cog...")
    print("Loading ExpManagement cog...")
    bot.add_cog(LevelingCog(bot))
    bot.add_cog(ExpManagementCog(bot))