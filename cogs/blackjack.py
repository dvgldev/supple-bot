import disnake
from disnake.ext import commands
from sqlalchemy import Column, Integer, String, Float, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import asyncio
import time
import random

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    discord_id = Column(String, unique=True)
    username = Column(String)
    balance = Column(Float, default=100)


DATABASE_URL = "sqlite:///testbot.db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)


CHANNEL_ID = 1258328686126563338

class BetModal(disnake.ui.Modal):
    def __init__(self, user, bot):
        components = [
            disnake.ui.TextInput(
                label="Введіть вашу ставку",
                custom_id="bet_amount",
                style=disnake.TextInputStyle.short,
                min_length=1,
                max_length=5
            )
        ]
        super().__init__(title="Зробити ставку", components=components)
        self.bot = bot

    async def callback(self, interaction: disnake.ModalInteraction):
        amount_input = interaction.text_values["bet_amount"]

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

        view = BlackjackView(user, amount, session, self.bot)
        await view.send_initial_embed(interaction)


class BlackJack(commands.Cog):
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
            title=":black_joker: Blackjack",
            description="```\nУ блекджеку кожен гравець грає з дилером (круп'є) віч-на-віч, незалежно від того, скільки гравців сидять за одним з ним столом; на результат гри для гравця жодним чином не впливають карти його сусіда по столу. Мета гри — набрати очок більше, ніж круп'є, але не більше 21.\n```",
            color=disnake.Color.green()
        )
        embed.add_field(name="**Мінімальні та максимальні ставки:**", value="150 - 5000 T-COINS.", inline=False)
        embed.add_field(name="**Правила гри у Blackjack:**", value=f"[Клік сюди](https://uk.wikipedia.org/wiki/%D0%91%D0%BB%D0%B5%D0%BA%D0%B4%D0%B6%D0%B5%D0%BA#:~:text=%D0%A8%D0%B5%D1%81%D1%82%D0%B8%D0%BA%D0%BE%D0%BB%D0%BE%D0%B4%D0%BD%D0%B8%D0%B9%20%D0%B1%D0%BB%D0%B5%D0%BA%D0%B4%D0%B6%D0%B5%D0%BA-,%D0%9F%D1%80%D0%B0%D0%B2%D0%B8%D0%BB%D0%B0%20%D0%B3%D1%80%D0%B8%20%D0%B2%20%D1%82%D1%80%D0%B0%D0%B4%D0%B8%D1%86%D1%96%D0%B9%D0%BD%D0%B8%D0%B9%20%D0%B1%D0%BB%D0%B5%D0%BA%D0%B4%D0%B6%D0%B5%D0%BA,-%5B%D1%80%D0%B5%D0%B4.)", inline=False)
        embed.set_image(url="https://wallpapers.com/images/hd/blackjack-dealer-placing-cards-2dyqkdw35nxa203h.jpg")
        embed.set_footer(text="Натисніть 'Грати', щоб почати гру.")

        await channel.send(embed=embed)
        await channel.send(view=StartBlackjackView(self.bot))

        
class StartBlackjackView(disnake.ui.View):
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

        await interaction.response.send_modal(BetModal(user, self.bot))


class BlackjackView(disnake.ui.View):
    def __init__(self, user, amount, session, bot):
        super().__init__(timeout=120)
        self.user = user
        self.amount = amount
        self.session = session
        self.bot = bot
        self.player_hand = []
        self.dealer_hand = []
        self.deck = self.create_deck()
        self.player_score = 0
        self.dealer_score = 0

        self.deal_initial_cards()

    def create_deck(self):
        deck = []
        suits = [":hearts:", ":diamonds:", ":clubs:", ":spades:"]
        values = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "Валет", "Дама", "Король", "Туз"]
        for suit in suits:
            for value in values:
                deck.append((value, suit))
        random.shuffle(deck)
        return deck

    def deal_initial_cards(self):
        self.player_hand.append(self.deck.pop())
        self.player_hand.append(self.deck.pop())
        self.dealer_hand.append(self.deck.pop())
        self.dealer_hand.append(self.deck.pop())
        self.update_scores()

    def update_scores(self):
        self.player_score = self.calculate_score(self.player_hand)
        self.dealer_score = self.calculate_score(self.dealer_hand)

    def calculate_score(self, hand):
        score = 0
        ace_count = 0
        for card in hand:
            value = card[0]
            if value in ["Валет", "Дама", "Король"]:
                score += 10
            elif value == "Туз":
                ace_count += 1
                score += 11
            else:
                score += int(value)

        while score > 21 and ace_count > 0:
            score -= 10
            ace_count -= 1

        return score

    def hand_to_string(self, hand):
        return ", ".join([f"{value} {suit}" for value, suit in hand])

    async def send_initial_embed(self, interaction):
        embed = disnake.Embed(title="🃏 Blackjack", color=0x007FFF)
        embed.add_field(name="Ваші карти:", value=self.hand_to_string(self.player_hand), inline=False)
        embed.add_field(name=" ", value=" ", inline=False)
        embed.add_field(name="Карти дилера:", value=f"{self.dealer_hand[0][0]} {self.dealer_hand[0][1]}, Hidden", inline=False)
        embed.add_field(name=" ", value=" ", inline=False)
        embed.set_footer(text="Натисніть Hit, щоб взяти карту або Stand, щоб залишитися на місці.")
        await interaction.response.send_message(embed=embed, view=self, ephemeral=True)

    @disnake.ui.button(label="Hit", style=disnake.ButtonStyle.primary)
    async def hit(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        self.player_hand.append(self.deck.pop())
        self.update_scores()

        if self.player_score > 21:
            await self.end_game(interaction, "**❌ Ви програли!** Ваш результат більше 21.")
        else:
            await self.send_update_embed(interaction)

    @disnake.ui.button(label="Stand", style=disnake.ButtonStyle.danger)
    async def stand(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        while self.dealer_score < 17:
            self.dealer_hand.append(self.deck.pop())
            self.update_scores()

        if self.dealer_score > 21 or self.player_score > self.dealer_score:
            await self.end_game(interaction, "**🎉 Ви виграли!** Ваш результат більше ніж у дилера.")
        elif self.player_score < self.dealer_score:
            await self.end_game(interaction, "**❌ Ви програли!** Ваш результат менше ніж у дилера.")
        else:
            await self.end_game(interaction, "**✖ Нічия!** Ваш результат дорівнює результату дилера.")

    async def send_update_embed(self, interaction):
        embed = disnake.Embed(title="🃏 Blackjack", color=0x007FFF)
        embed.add_field(name="Ваші карти:", value=self.hand_to_string(self.player_hand), inline=False)
        embed.add_field(name=" ", value=" ", inline=False)
        embed.add_field(name="Карти дилера:", value=f"{self.dealer_hand[0][0]} {self.dealer_hand[0][1]}, Hidden", inline=False)
        embed.add_field(name=" ", value=" ", inline=False)
        embed.set_footer(text="Натисніть Hit, щоб взяти карту або Stand, щоб залишитися на місці.")
        await interaction.response.edit_message(embed=embed, view=self)

    async def end_game(self, interaction, result):
        if "Ви виграли" in result:
            self.user.balance += self.amount
            print(f"Користувач {self.user.username} переміг дилера у блекджек та отримав {self.amount} T-COINS. Баланс користувача: {self.user.balance} T-COINS.")
        elif "Ви програли" in result:
            self.user.balance -= self.amount
            print(f"Користувач {self.user.username} програв дилеру у блекджек та втратив {self.amount} T-COINS. Баланс користувача: {self.user.balance} T-COINS.")

        self.session.commit()

        embed = disnake.Embed(title="🃏 Blackjack", description=result, color=0x007FFF)
        embed.add_field(name="Ваші карти:", value=self.hand_to_string(self.player_hand), inline=False)
        embed.add_field(name=" ", value=" ", inline=False)
        embed.add_field(name="Карти дилера:", value=self.hand_to_string(self.dealer_hand), inline=False)
        embed.add_field(name=" ", value=" ", inline=False)
        embed.set_footer(text=f"Баланс: {self.user.balance} T-COINS.", icon_url=interaction.author.display_avatar.url)
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()


def setup(bot):
    print("Loading Blackjack cog...")
    bot.add_cog(BlackJack(bot))