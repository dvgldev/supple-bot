import disnake
from disnake.ext import commands
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine
import random

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    discord_id = Column(String, unique=True)
    username = Column(String)
    balance = Column(Float, default=100)
    last_played = Column(DateTime, nullable=True)

DATABASE_URL = "sqlite:///testbot.db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

CHANNEL_ID = 1258328820600012800

class RouletteBetModal(disnake.ui.Modal):
    def __init__(self, user, bot):
        components = [
            disnake.ui.TextInput(
                label="Введіть вашу ставку",
                custom_id="bet_amount",
                style=disnake.TextInputStyle.short,
                min_length=1,
                max_length=5
            ),
            disnake.ui.TextInput(
                label="Тип ставки (🔴, ⚫, 🟢, число 1-36)",
                custom_id="bet_type",
                style=disnake.TextInputStyle.short,
                min_length=1,
                max_length=10
            )
        ]
        super().__init__(title="Зробити ставку на рулетку", components=components)
        self.bot = bot

    async def callback(self, interaction: disnake.ModalInteraction):
        amount_input = interaction.text_values["bet_amount"]
        bet_type = interaction.text_values["bet_type"].lower()

        try:
            amount = float(amount_input)
        except ValueError:
            await interaction.response.send_message("**❌ Помилка:** Будь ласка, введіть коректну суму.", ephemeral=True)
            return

        if amount < 150 or amount > 5000:
            await interaction.response.send_message("**❌ Помилка:** Ставка повинна бути від 150 до 5000 T-COINS.", ephemeral=True)
            return

        session = Session()
        discord_id = str(interaction.author.id)
        user = session.query(User).filter_by(discord_id=discord_id).first()
        if user is None:
            user = User(discord_id=discord_id, username=interaction.author.display_name)
            session.add(user)
            session.commit()

        if user.balance < amount:
            await interaction.response.send_message("**❌ Помилка:** У вас недостатньо коштів для ставки.", ephemeral=True)
            session.close()
            return

        result = self.play_roulette()
        result_color = self.get_color(result)
        payout = self.calculate_payout(bet_type, result)

        if payout > 0:
            user.balance += amount * payout
            result_message = f"**🎉 Ви виграли!** Результат: {result} {result_color}. Ваша ставка на {bet_type} принесла Вам **{amount * payout}** T-COINS. Новий баланс: **{user.balance}** T-COINS."
            print(f"Користувач {user.username} переміг дилера у рулетку та отримав {amount} T-COINS. Результат: {result} {result_color}. Баланс користувача: {user.balance} T-COINS.")
        else:
            user.balance -= amount
            result_message = f"**❌ Ви програли.** Результат: {result} {result_color}. Ваша ставка на {bet_type} не принесла виграшу. Новий баланс: **{user.balance}** T-COINS."
            print(f"Користувач {user.username} програв дилеру у рулетку та втратив {amount} T-COINS. Результат: {result} {result_color}. Баланс користувача: {user.balance} T-COINS.")

        session.commit()
        await interaction.response.send_message(result_message, ephemeral=True)

    def play_roulette(self):
        return random.randint(0, 36)

    def get_color(self, result):
        red_numbers = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
        black_numbers = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}
        if result in red_numbers:
            return "червоне"
        elif result in black_numbers:
            return "чорне"
        else:
            return "зелене"

    def calculate_payout(self, bet_type, result):
        red_numbers = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
        black_numbers = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}

        if bet_type == "червоне" and result in red_numbers:
            return 1
        elif bet_type == "чорне" and result in black_numbers:
            return 1
        elif bet_type.isdigit() and int(bet_type) == result:
            return 36
        else:
            return 0


class StartRouletteView(disnake.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @disnake.ui.button(label="Грати", style=disnake.ButtonStyle.success)
    async def start_game(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        session = Session()
        discord_id = str(interaction.author.id)
        user = session.query(User).filter_by(discord_id=discord_id).first()
        if user is None:
            user = User(discord_id=discord_id, username=interaction.author.display_name)
            session.add(user)
            session.commit()

        await interaction.response.send_modal(RouletteBetModal(user, self.bot))


class Roulette(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        channel = self.bot.get_channel(CHANNEL_ID)

        messages = await channel.history(limit=10).flatten()
        for message in messages:
            if message.author == self.bot.user:
                await message.delete()

        embed = disnake.Embed(
            title=":slot_machine: Рулетка",
            description="```\nРулетка — азартна гра, що представляє собою колесо, що обертається з 36 секторами червоного і чорного кольорів і 37-м зеленим сектором «зеро» з позначенням нуля. Гравці, які грають у рулетку, можуть зробити ставку на випадання кульки на колір (червоне або червоне) або конкретне число. Круп'є запускає кульку над колесом рулетки, який рухається убік, протилежний обертанню колеса рулетки, і врешті-решт випадає на один із секторів. Виграші отримують усі, чия ставка зіграла.\n\nДля того, щоб правильно ввести тип ставки - вводіть у поле слово 'червоне', 'чорне' або 'зелене'. Якщо Ви вирішили зробити ставку на число - просто введіть його, без кольору.```",
            color=disnake.Color.green()
        )
        embed.add_field(name="**Мінімальні та максимальні ставки:**", value="150 - 5000 T-COINS.", inline=False)
        embed.add_field(name="**Правила гри у рулетку:**", value=f"[Клік сюди](https://uk.wikipedia.org/wiki/%D0%90%D0%BC%D0%B5%D1%80%D0%B8%D0%BA%D0%B0%D0%BD%D1%81%D1%8C%D0%BA%D0%B0_%D1%80%D1%83%D0%BB%D0%B5%D1%82%D0%BA%D0%B0#:~:text=%D0%BE%D1%82%D1%80%D0%B8%D0%BC%D1%83%D1%8E%D1%82%D1%8C%20%D1%81%D0%B2%D0%BE%D1%97%20%D0%B2%D0%B8%D0%B3%D1%80%D0%B0%D1%88%D1%96.-,%D0%A1%D1%82%D0%B0%D0%B2%D0%BA%D0%B8%20%D0%B2%20%D0%B0%D0%BC%D0%B5%D1%80%D0%B8%D0%BA%D0%B0%D0%BD%D1%81%D1%8C%D0%BA%D1%96%D0%B9%20%D1%80%D1%83%D0%BB%D0%B5%D1%82%D1%86%D1%96,-%5B%D1%80%D0%B5%D0%B4.)", inline=False)
        embed.set_image(url="https://img.freepik.com/premium-vector/european-casino-roulette-scheme-layout-table-template-design-online-game-vector-illustration-isolated-green-background_529424-35.jpg")
        embed.set_footer(text="Натисніть 'Грати', щоб почати гру.")

        await channel.send(embed=embed)
        await channel.send(view=StartRouletteView(self.bot))


def setup(bot):
    print("Loading Roulette cog...")
    bot.add_cog(Roulette(bot))