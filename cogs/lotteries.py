import disnake
from disnake.ext import commands
from disnake.ext.commands import has_role, Bot
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime, timedelta
import random
import asyncio
import pytz

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    discord_id = Column(String, unique=True)
    username = Column(String)
    balance = Column(Float, default=100)
    last_played = Column(DateTime, nullable=True)
    tickets = relationship("LotteryTicket", back_populates="user")

class Lottery(Base):
    __tablename__ = 'lotteries'
    id = Column(Integer, primary_key=True)
    prize = Column(Float)
    price = Column(Float)
    end_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    winner_username = Column(String, nullable=True)
    winner_discord_id = Column(String, nullable=True)
    message_id = Column(Integer, nullable=True)
    tickets = relationship("LotteryTicket", back_populates="lottery")

class LotteryTicket(Base):
    __tablename__ = 'lottery_tickets'
    id = Column(Integer, primary_key=True)
    lottery_id = Column(Integer, ForeignKey('lotteries.id'))
    discord_id = Column(String, ForeignKey('users.discord_id'), nullable=False)
    username = Column(String, nullable=False)
    user = relationship("User", back_populates="tickets")
    lottery = relationship("Lottery", back_populates="tickets")


DATABASE_URL = "sqlite:///testbot.db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)


CHANNEL_ID = 1258748443308982282
UKRAINE_TZ = pytz.timezone('Europe/Kiev')


class CreateLotteryModal(disnake.ui.Modal):
    def __init__(self, bot):
        components = [
            disnake.ui.TextInput(
                label="Приз (T-COINS)",
                custom_id="prize",
                style=disnake.TextInputStyle.short,
                min_length=1,
                max_length=10
            ),
            disnake.ui.TextInput(
                label="Ціна квитка (T-COINS)",
                custom_id="price",
                style=disnake.TextInputStyle.short,
                min_length=1,
                max_length=10
            ),
            disnake.ui.TextInput(
                label="Дата закінчення (YYYY-MM-DD HH:MM)",
                custom_id="end_date",
                style=disnake.TextInputStyle.short,
                min_length=16,
                max_length=16
            )
        ]
        super().__init__(title="Створити лотерею", components=components)
        self.bot = bot

    async def callback(self, interaction: disnake.ModalInteraction):
        prize = float(interaction.text_values["prize"])
        price = float(interaction.text_values["price"])
        end_date_str = interaction.text_values["end_date"]
        try:
            end_date_naive = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M')
            end_date = UKRAINE_TZ.localize(end_date_naive)
            print(f"Локалізований час завершення лотереї: {end_date}")
        except ValueError:
            await interaction.response.send_message("**❌ Помилка:** Некоректний формат дати.", ephemeral=True)
            return

        session = Session()
        new_lottery = Lottery(prize=prize, price=price, end_date=end_date)
        session.add(new_lottery)
        session.commit()
        print(f"Створена нова лотерея з ID: №{new_lottery.id}. Приз: {prize}, ціна квитка: {price}, час завершення: {end_date}.")

        embed = disnake.Embed(
            title=":ticket: Лотерея",
            description=(
                f"**Приз:** `{prize} T-COINS`.\n"
                f"**Ціна квитка:** `{price} T-COINS`.\n"
                f"**Дата та час закінчення:** `{end_date.strftime('%Y-%m-%d %H:%M %Z')}`.\n"
            ),
            color=disnake.Color.green()
        )
        embed.set_footer(text="Натисніть 'Купити квиток', щоб взяти участь у лотереї.")

        channel = self.bot.get_channel(CHANNEL_ID)
        message = await channel.send(embed=embed, view=BuyTicketView(self.bot, new_lottery.id))
        new_lottery.message_id = message.id
        session.commit()
        await interaction.response.send_message(f"✨ **Лотерея успішно створена!** Результат можна подивитися в каналі <#{CHANNEL_ID}>", ephemeral=True)
        session.close()

class BuyTicketView(disnake.ui.View):
    def __init__(self, bot, lottery_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.lottery_id = lottery_id

    @disnake.ui.button(label="Купити квиток", style=disnake.ButtonStyle.success)
    async def buy_ticket(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        session = Session()
        discord_id = str(interaction.author.id)
        user = session.query(User).filter_by(discord_id=discord_id).first()
        if user is None:
            user = User(discord_id=discord_id, username=interaction.author.display_name)
            session.add(user)
            session.commit()

        lottery = session.query(Lottery).filter_by(id=self.lottery_id).first()
        if not lottery.is_active:
            await interaction.response.send_message("**❌ Помилка:** Лотерея закінчилася.", ephemeral=True)
            session.close()
            return

        if user.balance < lottery.price:
            await interaction.response.send_message("**❌ Помилка:** У вас недостатньо коштів для покупки квитка.", ephemeral=True)
            session.close()
            return

        existing_ticket = session.query(LotteryTicket).filter_by(discord_id=discord_id, lottery_id=self.lottery_id).first()
        if existing_ticket:
            await interaction.response.send_message("**❌ Помилка:** Ви вже придбали квиток на цю лотерею.", ephemeral=True)
            session.close()
            return

        ticket = LotteryTicket(discord_id=discord_id, lottery_id=self.lottery_id, username=user.username)
        user.balance -= lottery.price
        session.add(ticket)
        session.commit()
        print(f"Користувач {user.username} купив квиток для лотереї №{self.lottery_id}.")
        await interaction.response.send_message("✨ **Квиток для участі у лотереї успішно куплений!** Результат очікуйте в цьому каналі в день та час завершення лотереї.", ephemeral=True)
        session.close()

class LotteryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="create_lottery", description="Створити лотерею.")
    @has_role(1239181262753890305)
    async def create_lottery(self, interaction: disnake.ApplicationCommandInteraction):
        await interaction.response.send_modal(CreateLotteryModal(self.bot))

    async def end_lottery(self, lottery_id):
        session = Session()
        lottery = session.query(Lottery).filter_by(id=lottery_id).first()
        if lottery:
            tickets = session.query(LotteryTicket).filter_by(lottery_id=lottery_id).all()
            if len(tickets) < 5:
                for ticket in tickets:
                    user = ticket.user
                    user.balance += lottery.price
                status_message = "Лотерея була скасована через недостатню кількість учасників. Кошти за квитки повернуті користувачам."
                print(f"Лотерея №{lottery_id} скасована через недостатню кількість учасників.")
                winner_mention = 'Немає'
            else:
                winner_ticket = random.choice(tickets)
                winner = winner_ticket.user
                winner.balance += lottery.prize
                lottery.winner_username = winner.username
                lottery.winner_discord_id = winner.discord_id
                status_message = "Лотерея успішно завершилася."
                print(f"Лотерея №{lottery_id} завершилася. Переможець: {winner.username}, приз: {lottery.prize} T-COINS.")
                winner_mention = f'<@{winner.discord_id}>'

            lottery.is_active = False
            session.commit()

            channel = self.bot.get_channel(CHANNEL_ID)
            try:
                old_message = await channel.fetch_message(lottery.message_id)
                await old_message.delete()
            except disnake.NotFound:
                pass

            embed = disnake.Embed(
                title=":tickets: Лотерея",
                description=(
                    f"**Приз:** `{lottery.prize} T-COINS`.\n"
                    f"**Ціна квитка:** `{lottery.price} T-COINS`.\n"
                    f"**Дата та час закінчення:** `{lottery.end_date.strftime('%Y-%m-%d %H:%M')}`.\n"
                    f"**Переможець:** {winner_mention}.\n"
                ),
                color=disnake.Color.red()
            )
            embed.set_footer(text=f"{status_message}")

            await channel.send(embed=embed)

        session.close()

    async def check_lotteries(self):
        session = Session()
        now = datetime.now(tz=UKRAINE_TZ)
        active_lotteries = session.query(Lottery).filter(Lottery.end_date <= now, Lottery.is_active == True).all()
        print(f"Перевірка лотерей на {now}. Знайдено активних лотерей: {len(active_lotteries)}")
        for lottery in active_lotteries:
            await self.end_lottery(lottery.id)
        session.close()

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.loop.create_task(self.lottery_check_loop())

    async def lottery_check_loop(self):
        while True:
            await self.check_lotteries()
            await asyncio.sleep(60)


def setup(bot: Bot):
    print("Loading Lotteries cog...")
    bot.add_cog(LotteryCog(bot))