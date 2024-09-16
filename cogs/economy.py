import disnake
from disnake.ext import commands
from sqlalchemy import Column, Integer, String, Float, ForeignKey, create_engine, desc, DateTime, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import asyncio
import time
import random
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    discord_id = Column(String, unique=True)
    username = Column(String)
    balance = Column(Float, default=100)

class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True)
    sender_id = Column(Integer, ForeignKey('users.id'))
    receiver_id = Column(Integer, ForeignKey('users.id'))
    amount = Column(Float)
    sender_username = Column(String)
    receiver_username = Column(String)
    timestamp = Column(DateTime, default=datetime.now)
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])


DATABASE_URL = "sqlite:///testbot.db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)


NOTIFICATION_CHANNEL_ID = 1236274638980649113


class Balance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot_messages_id = 1236274638980649113
        self.admin_role_id = 1239181262753890305
        self.last_transaction_time = {}
        self.last_daily_time = {}

    @commands.Cog.listener()
    async def on_member_join(self, member):
        session = Session()
        discord_id = str(member.id)
        username = member.display_name
        user = session.query(User).filter_by(discord_id=discord_id).first()
        if not user:
            user = User(discord_id=discord_id, username=username)
            session.add(user)
            session.commit()
        session.close()

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        session = Session()
        discord_id = str(member.id)
        user = session.query(User).filter_by(discord_id=discord_id).first()
        if user:
            user.balance = 0
            session.commit()
        session.close()

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.display_name != after.display_name:
            session = Session()
            discord_id = str(after.id)
            user = session.query(User).filter_by(discord_id=discord_id).first()
            if user:
                user.username = after.display_name
                session.commit()
            session.close()

    @commands.slash_command(name="balance", description="Перевірити свій баланс.")
    async def balance(self, inter):
        await inter.response.defer(ephemeral=True)

        discord_id = str(inter.author.id)
        session = Session()
        user = session.query(User).filter_by(discord_id=discord_id).first()
        session.close()

        if user:
            embed = disnake.Embed(
                title=" ",
                description=
                f":credit_card: `T-COINS`: **{user.balance}**.\n"
                f":coin: `Bitcoin`: **Unknown**.",
                color=0x007FFF
            )
            embed.add_field(name="", value="", inline=False)
            embed.set_footer(text=f"Баланс користувача: {inter.author.display_name}.", icon_url=inter.author.display_avatar.url)
            await inter.edit_original_response(embed=embed)
        else:
            await inter.edit_original_response(content="**❌ Помилка:** Ваш акаунт не знайдено, зверніться до технічного адміністратора.")

    @commands.slash_command(name="pay", description="Передати T-COINS іншому користувачу.")
    async def pay(self, inter, receiver: disnake.User, amount: float):
        sender_id = str(inter.author.id)
        receiver_id = str(receiver.id)
        sender_username = inter.author.display_name
        receiver_username = receiver.display_name

        if sender_id == receiver_id:
            await inter.response.send_message("**❌ Помилка:** Ви не можете відправити T-COINS самому собі.", ephemeral=True)
            return

        if amount > 10000:
            await inter.response.send_message("**❌ Помилка:** Ліміт на переказ між користувачами 10.000 T-COINS.", ephemeral=True)
            return

        current_time = time.time()
        if sender_id in self.last_transaction_time:
            last_time = self.last_transaction_time[sender_id]
            if current_time - last_time < 300:
                remaining_time = 300 - (current_time - last_time)
                minutes = int(remaining_time // 60)
                seconds = int(remaining_time % 60)
                await inter.response.send_message(
                    f"**❌ Помилка:** Ви зможете зробити наступний переказ через {minutes} хв. {seconds} с.",
                    ephemeral=True
                )
                return

        session = Session()
        sender = session.query(User).filter_by(discord_id=sender_id).first()
        receiver_user = session.query(User).filter_by(discord_id=receiver_id).first()

        if not sender or sender.balance < amount:
            await inter.response.send_message("**❌ Помилка:** У вас недостатньо коштів.", ephemeral=True)
            session.close()
            return

        if not receiver_user:
            receiver_user = User(discord_id=receiver_id, username=receiver_username, balance=100)
            session.add(receiver_user)
            session.commit()

        sender.balance -= amount
        receiver_user.balance += amount
        transaction = Transaction(
            sender_id=sender.id,
            receiver_id=receiver_user.id,
            amount=amount,
            sender_username=sender_username,
            receiver_username=receiver_username
        )
        session.add(transaction)
        session.commit()
        session.close()

        self.last_transaction_time[sender_id] = current_time

        channel = self.bot.get_channel(NOTIFICATION_CHANNEL_ID)
        embed = disnake.Embed(
            title=" ",
            description=f"💸 Користувач {inter.author.mention} передав користувачу {receiver.mention} **{amount}** T-COINS.",
            color=disnake.Color.green()
        )
        print(f"Користувач {sender_username} передав користувачу {receiver_username} {amount} T-COINS.")
        await channel.send(embed=embed)

        await inter.response.send_message(f"💸 Ви успішно передали **{amount}** T-COINS користувачу **{receiver.mention}**.", ephemeral=True)

    @commands.slash_command(name="coin", description="Гра 'Орел або решка'.")
    async def coin(self, inter, amount: float):
        user_id = str(inter.author.id)
        session = Session()
        user = session.query(User).filter_by(discord_id=user_id).first()

        if not user or user.balance < amount:
            await inter.response.send_message("**❌ Помилка:** У вас недостатньо коштів для ставки.", ephemeral=True)
            session.close()
            return

        if amount < 150 or amount > 5000:
            await inter.response.send_message("**❌ Помилка:** Ставка повинна бути від **150** до **5.000** T-COINS.", ephemeral=True)
            session.close()
            return

        await inter.response.send_message("🎲 Для того, щоб почати гру Вам потрібно обрати `орла` або `решку`!\n", ephemeral=True, view=CoinView(user, amount, session, self.bot))

    @commands.slash_command(name="give_coin", description="Видати T-COINS користувачу.")
    async def give_coin(self, inter, user: disnake.User, amount: float):
        if self.admin_role_id not in [role.id for role in inter.author.roles]:
            await inter.response.send_message("**❌ Помилка:** Ви не маєте доступу до використання цієї команди.", ephemeral=True)
            return

        session = Session()
        target_user = session.query(User).filter_by(discord_id=str(user.id)).first()

        if not target_user:
            target_user = User(discord_id=str(user.id), username=user.display_name, balance=100)
            session.add(target_user)
            session.commit()

        target_user.balance += amount
        session.commit()

        target_username = target_user.username
        author_display_name = inter.author.display_name

        session.close()

        await inter.response.send_message(f"💸 Ви успішно видали **{amount}** T-COINS користувачу **{user.mention}**.", ephemeral=True)
        await asyncio.sleep(3)

        channel = self.bot.get_channel(NOTIFICATION_CHANNEL_ID)
        embed = disnake.Embed(
            title=" ",
            description=f"💸 Модератор {inter.author.mention} видав користувачу {user.mention} **{amount}** T-COINS.",
            color=disnake.Color.green()
        )
        await channel.send(embed=embed)
        print(f"Модератор {author_display_name} видав користувачу {target_username} {amount} T-COINS.")


    @commands.slash_command(name="take_coin", description="Забрати T-COINS у користувача.")
    async def take_coin(self, inter, user: disnake.User, amount: float):
        if self.admin_role_id not in [role.id for role in inter.author.roles]:
            await inter.response.send_message("**❌ Помилка:** Ви не маєте доступу до використання цієї команди.", ephemeral=True)
            return

        session = Session()
        target_user = session.query(User).filter_by(discord_id=str(user.id)).first()

        if not target_user or target_user.balance < amount:
            await inter.response.send_message("**❌ Помилка:** У користувача недостатньо коштів.", ephemeral=True)
            session.close()
            return

        target_user.balance -= amount
        session.commit()

        target_username = target_user.username
        author_display_name = inter.author.display_name

        session.close()

        await inter.response.send_message(f"💔 Ви успішно забрали **{amount}** T-COINS у користувача **{user.mention}**.", ephemeral=True)
        await asyncio.sleep(3)

        channel = self.bot.get_channel(NOTIFICATION_CHANNEL_ID)
        embed = disnake.Embed(
            title=" ",
            description=f"❌ Модератор {inter.author.mention} забрав у користувача {user.mention} **{amount}** T-COINS.",
            color=disnake.Color.red()
        )
        await channel.send(embed=embed)
        print(f"Модератор {author_display_name} забрав у користувача {target_username} {amount} T-COINS.")


    @commands.slash_command(name="daily", description="Отримати тимчасову винагороду.")
    async def daily(self, inter):
        user_id = str(inter.author.id)
        current_time = time.time()

        if user_id in self.last_daily_time:
            last_reward_time = self.last_daily_time[user_id]
            if current_time - last_reward_time < 28800:
                remaining_time = 28800 - (current_time - last_reward_time)
                hours = int(remaining_time // 3600)
                minutes = int((remaining_time % 3600) // 60)
                seconds = int(remaining_time % 60)
                await inter.response.send_message(f"**❌ Помилка:** Ви зможете отримати наступну винагороду через {hours} год. {minutes} хв. {seconds} с.", ephemeral=True)
                return

        session = Session()

        try:
            user = session.query(User).filter_by(discord_id=user_id).first()

            if not user:
                await inter.response.send_message("**❌ Помилка:** Ваш акаунт не знайдено, зверніться до технічного адміністратора.", ephemeral=True)
                return

            user.balance += 50
            session.commit()

            self.last_daily_time[user_id] = current_time

            await inter.response.send_message(f"🎉 Ви отримали тимчасову винагороду у розмірі **50** T-COINS. Ваш новий баланс: **{user.balance}** T-COINS.", ephemeral=True)

        except Exception as e:
            session.rollback()
            raise e

        finally:
            session.close()

    @commands.slash_command(name="transactions", description="Переглянути останні транзакції.")
    async def transactions(self, inter):
        session = Session()

        try:
            discord_id = str(inter.author.id)
            user = session.query(User).filter_by(discord_id=discord_id).first()

            if not user:
                await inter.response.send_message("**❌ Помилка:** Ваш акаунт не знайдено, зверніться до технічного адміністратора.", ephemeral=True)
                return

            transactions = session.query(Transaction).filter(
                or_(Transaction.sender_id == user.id, Transaction.receiver_id == user.id)
            ).order_by(Transaction.timestamp.desc()).limit(5).all()

            if not transactions:
                await inter.response.send_message("**❌ Помилка:** Немає жодних транзакцій для відображення.", ephemeral=True)
                return

            embed = disnake.Embed(
                title="Останні транзакції",
                description=" ",
                color=0x007FFF
            )

            for transaction in transactions:
                if transaction.sender_id == user.id:
                    sender_mention = inter.author.mention
                    receiver_mention = self.bot.get_user(int(transaction.receiver.discord_id)).mention
                else:
                    sender_mention = self.bot.get_user(int(transaction.sender.discord_id)).mention
                    receiver_mention = inter.author.mention

                transaction_time = transaction.timestamp.strftime("%Y-%m-%d %H:%M:%S")

                embed.add_field(
                    name=f"Транзакція #{transaction.id}:",
                    value=f":money_with_wings: {sender_mention} :arrow_right: {receiver_mention}: **{transaction.amount}** T-COINS.\n"
                        f":clock4: `{transaction_time}`.",
                    inline=False
                )
                embed.set_footer(text=f"Баланс: {user.balance} T-COINS.", icon_url=inter.author.display_avatar.url)

            await inter.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await inter.response.send_message(f"**❌ Помилка:** Виникла помилка під час обробки запиту: {e}", ephemeral=True)
            raise e

        finally:
            session.close()


class CoinView(disnake.ui.View):
    def __init__(self, user, amount, session, bot):
        super().__init__(timeout=60)
        self.user = user
        self.amount = amount
        self.session = session
        self.bot = bot

    @disnake.ui.button(label="🦅 Орел", style=disnake.ButtonStyle.secondary)
    async def heads(self, button: disnake.ui.Button, inter: disnake.Interaction):
        await self.play_game(inter, "heads")

    @disnake.ui.button(label=f"🎭 Решка", style=disnake.ButtonStyle.secondary)
    async def tails(self, button: disnake.ui.Button, inter: disnake.Interaction):
        await self.play_game(inter, "tails")

    async def play_game(self, inter, choice):
        result = random.choice(["heads", "tails"])
        if choice == result:
            self.user.balance += self.amount
            result_msg = f"🎉 Вітаємо! Ви виграли **{self.amount}** T-COINS."
            print(f"Користувач {self.user.username} переміг у коін-фліпі та отримав {self.amount} T-COINS. Баланс користувача: {self.user.balance} T-COINS.")
        else:
            self.user.balance -= self.amount
            result_msg = f"😢 Ви програли **{self.amount}** T-COINS."
            print(f"Користувач {self.user.username} програв у коін-фліпі та втратив {self.amount} T-COINS. Баланс користувача: {self.user.balance} T-COINS.")

        self.session.commit()
        self.session.close()

        await inter.response.edit_message(content=result_msg, view=None)


def setup(bot):
    print("Loading Economy cog...")
    bot.add_cog(Balance(bot))