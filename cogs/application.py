import disnake
from disnake.ext import commands
from disnake.ui import Button, View, Modal, TextInput
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import enum

APPLICATION_CHANNEL_ID = 1252946964664815636
RESPONSE_CHANNEL_ID = 1252947041810780201
ROLE_MENTION_ID = 1253059030327234570
APPROVAL_ROLE_ID = 1253289761611972708

Base = declarative_base()

class ApplicationStatus(enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

class Application(Base):
    __tablename__ = 'applications'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    user_mention = Column(String)
    name = Column(String)
    age = Column(String)
    reason = Column(String)
    friend = Column(String)
    rules_response = Column(Boolean)
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.pending)

DATABASE_URL = "sqlite:///testbot.db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

Base.metadata.create_all(engine)

class ApplicationModal(Modal):
    def __init__(self, user_mention):
        components = [
            TextInput(label="1. Ваш майбутній нікнейм:", placeholder="Введіть ваш майбутній нікнейм", custom_id="name_input"),
            TextInput(label="2. Ваш вік:", placeholder="Введіть ваш реальний вік", custom_id="age_input"),
            TextInput(label="3. Як давно Ви приєдналися до серверу?", placeholder="Ваша відповідь", custom_id="reason_input"),
            TextInput(label="4. Ви плануєте грати з друзями чи поодинці?", placeholder="Ваша відповідь", custom_id="friend_input", required=False)
        ]
        super().__init__(title="Заявка у вайт-лист сервера TEST SERVER", components=components)
        self.user_mention = user_mention
    
    async def callback(self, inter: disnake.ModalInteraction):
        name = inter.text_values["name_input"]
        age = inter.text_values["age_input"]
        reason = inter.text_values["reason_input"]
        friend = inter.text_values["friend_input"]

        await inter.response.send_message(
            "Чи ознайомлені Ви з правилами серверу?",
            view=RulesButtonView(name, age, reason, friend, inter.author.id, self.user_mention),
            ephemeral=True
        )

class RulesButtonView(View):
    def __init__(self, name, age, reason, friend, user_id, user_mention):
        super().__init__(timeout=None)
        self.name = name
        self.age = age
        self.reason = reason
        self.friend = friend
        self.user_id = user_id
        self.user_mention = user_mention

        button_yes = Button(label="Так", style=disnake.ButtonStyle.primary, custom_id="rules_yes")
        button_no = Button(label="Ні", style=disnake.ButtonStyle.danger, custom_id="rules_no")

        button_yes.callback = self.button_callback
        button_no.callback = self.button_callback

        self.add_item(button_yes)
        self.add_item(button_no)

    async def button_callback(self, button_inter: disnake.MessageInteraction):
        rules_response = True if button_inter.component.label == "Так" else False

        session = Session()
        application = Application(
            user_id=self.user_id,
            user_mention=self.user_mention,
            name=self.name,
            age=self.age,
            reason=self.reason,
            friend=self.friend,
            rules_response=rules_response
        )
        session.add(application)
        session.commit()
        session.close()

        await self.send_application(button_inter, "Так" if rules_response else "Ні")

        for item in self.children:
            item.disabled = True
        await button_inter.response.edit_message(view=self)

    async def send_application(self, inter: disnake.MessageInteraction, rules_response: str):
        role_mention = inter.guild.get_role(ROLE_MENTION_ID).mention

        embed = disnake.Embed(title=" ", color=disnake.Color.green())
        embed.add_field(name="1. Нікнейм користувача:", value=self.name, inline=False)
        embed.add_field(name=" ", value=" ", inline=False)
        embed.add_field(name="2. Вік користувача:", value=self.age, inline=False)
        embed.add_field(name=" ", value=" ", inline=False)
        embed.add_field(name="3. Як давно приєднався(-лася) до серверу:", value=self.reason, inline=False)
        embed.add_field(name=" ", value=" ", inline=False)
        embed.add_field(name="4. Гра поодинці чи друзями?", value=self.friend, inline=False)
        embed.add_field(name=" ", value=" ", inline=False)
        embed.add_field(name="5. Чи ознайомлений(-на) з правилами серверу?", value=rules_response, inline=False)
        
        channel = inter.guild.get_channel(RESPONSE_CHANNEL_ID)
        await channel.send(f"**{role_mention}, нова заявка на реєстрації у вайт-ліст сервера!**\n\nВідправник(-ця): {self.user_mention}", embed=embed, view=ApprovalView(self.user_id))

class ApprovalView(View):
    def __init__(self, applicant_id):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id
        button_approve = Button(label="Схвалити", style=disnake.ButtonStyle.success, custom_id="approve")
        button_reject = Button(label="Відхилити", style=disnake.ButtonStyle.danger, custom_id="reject")
        button_approve.callback = self.approve_callback
        button_reject.callback = self.reject_callback
        self.add_item(button_approve)
        self.add_item(button_reject)

    async def approve_callback(self, button_inter: disnake.MessageInteraction):
        session = Session()
        member = button_inter.guild.get_member(self.applicant_id)
        role = button_inter.guild.get_role(APPROVAL_ROLE_ID)

        if member:
            await member.add_roles(role)
            await member.send("**🙌 Ваша заявка на вайт-лист була схвалена!**\nДотримуйтесь правил сервера та бажаємо Вам приємної гри!")
            await button_inter.response.send_message(f"✨ Модератор {button_inter.user.mention} **схвалив** заявку користувача {member.mention}.", ephemeral=False)

            application = session.query(Application).filter_by(user_id=self.applicant_id, status=ApplicationStatus.pending).first()
            if application:
                application.status = ApplicationStatus.approved
                session.commit()
        else:
            await button_inter.response.send_message(f"**❌ Помилка**: Не вдалося знайти користувача для видачі ролі.", ephemeral=True)

        for item in self.children:
            item.disabled = True
        await button_inter.message.edit(view=self)
        session.close()

    async def reject_callback(self, button_inter: disnake.MessageInteraction):
        session = Session()
        member = button_inter.guild.get_member(self.applicant_id)

        if member:
            await member.send("**❌ Ваша заявка на вайт-лист була відхилена.**\nБудь ласка, зверніться до крафтмайстерів за подробицями в особисті повідомлення.")
            await button_inter.response.send_message(f"❌ Модератор {button_inter.user.mention} **відхилив** заявку користувача {member.mention}.", ephemeral=False)

            application = session.query(Application).filter_by(user_id=self.applicant_id, status=ApplicationStatus.pending).first()
            if application:
                application.status = ApplicationStatus.rejected
                session.commit()
        else:
            await button_inter.response.send_message(f"**❌ Помилка**: Не вдалося знайти користувача для відправлення повідомлення.", ephemeral=True)

        for item in self.children:
            item.disabled = True
        await button_inter.message.edit(view=self)
        session.close()

class ApplicationView(View):
    def __init__(self):
        super().__init__(timeout=None)
        button = Button(label="Подати заявку", style=disnake.ButtonStyle.secondary)
        button.callback = self.apply_button_callback
        self.add_item(button)

    async def apply_button_callback(self, button_inter: disnake.MessageInteraction):
        user_id = button_inter.user.id
        session = Session()

        existing_application = session.query(Application).filter_by(user_id=user_id, status=ApplicationStatus.pending).first()
        if existing_application:
            await button_inter.response.send_message("**❌ Помилка**: Ваша попередня заявка ще не перевірена. Будь ласка, зачекайте поки її розглянуть.", ephemeral=True)
            session.close()
            return

        last_application = session.query(Application).filter_by(user_id=user_id).order_by(Application.timestamp.desc()).first()
        if last_application and (datetime.utcnow() - last_application.timestamp) < timedelta(minutes=10):
            await button_inter.response.send_message("**❌ Помилка**: Ви можете подати нову заявку лише раз на 10 хвилин. Будь ласка, спробуйте пізніше.", ephemeral=True)
            session.close()
            return

        modal = ApplicationModal(button_inter.user.mention)
        await button_inter.response.send_modal(modal)
        session.close()

class ApplicationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        channel = self.bot.get_channel(APPLICATION_CHANNEL_ID)
        view = ApplicationView()
        
        async for message in channel.history(limit=100):
            if message.author == self.bot.user and message.embeds:
                embed = message.embeds[0]
                if (embed.title == "Заявка на слот у вайт-листі сервера TEST SERVER" and
                    "Ви маєте можливість пройти попередню реєстрацію, яка надасть доступ до приватних каналів та додасть ваш нікнейм до вайт-лісту. \nДля того, щоб подати заявку – __натисніть на кнопку нижче!__" in embed.description):
                    await message.edit(view=view)
                    return

        embed = disnake.Embed(
            title="Заявка на слот у вайт-листі сервера TEST SERVER", 
            description="Ви маєте можливість пройти попередню реєстрацію, яка надасть доступ до приватних каналів та додасть ваш нікнейм до вайт-лісту. \nДля того, щоб подати заявку – __натисніть на кнопку нижче!__", 
            color=0xF1F1F1
        )
        embed.add_field(name=" ", value=" ", inline=False)
        embed.add_field(name="**Критерії для вступу:**", value="• Пачка сухариків Флінт зі смаком сметани та зелені;\n• 10+ lvl на сервері в дискорді.", inline=False)
        embed.set_image(url="https://cdn-media-1.freecodecamp.org/images/1*MirHqdGmQeG2kH_CuAkyow.jpeg")
        embed.set_footer(text='З повагою, крафтмайстери TEST SERVER 🤍', icon_url=self.bot.user.avatar.url)
        await channel.send(embed=embed, view=view)

def setup(bot):
    print("Loading Application cog...")
    bot.add_cog(ApplicationCog(bot))
