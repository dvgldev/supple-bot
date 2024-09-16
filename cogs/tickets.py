import disnake
from disnake.ext import commands
from datetime import datetime

class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ticket_channel_id = 1239181525862453318
        self.mod_role_id = 1239181262753890305
        self.ticket_category_id = 1239181486775603232
        self.tickets = {}
        self.mod_role = None


    @commands.Cog.listener()
    async def on_ready(self):
        self.ticket_channel = self.bot.get_channel(self.ticket_channel_id)
        self.ticket_category = self.bot.get_channel(self.ticket_category_id)
        guild = self.ticket_channel.guild
        self.mod_role = guild.get_role(self.mod_role_id)
        await self.create_ticket_button()


    async def create_ticket_button(self):
        async for message in self.ticket_channel.history(limit=100):
            if message.author == self.bot.user and message.embeds and any(item.custom_id == "create_ticket_button" for item in message.components[0].children):
                return

        embed = disnake.Embed(
            title="Тікет-система",
            description="Тікет-система – інструмент для спілкування між користувачами та модераторами. Звертаючись до модераторів з питанням, пропозицією або проблемою, ви можете очікувати на швидку реакцію.\n\n**Щоб відправити тікет модераторам – натисніть кнопку нижче!**",
            color=0x007FFF
        )
        button = disnake.ui.Button(label="💬 Створити тікет", style=disnake.ButtonStyle.primary, custom_id="create_ticket_button")
        await self.ticket_channel.send(embed=embed, view=disnake.ui.View().add_item(button))


    @commands.Cog.listener()
    async def on_button_click(self, interaction: disnake.MessageInteraction):
        if interaction.component.custom_id == "create_ticket_button":
            await self.create_ticket_callback(interaction)
        elif interaction.component.custom_id.startswith("close_ticket_button"):
            await self.close_ticket_callback(interaction)


    async def create_ticket_callback(self, interaction):
        if interaction.user.id in self.tickets:
            await interaction.response.send_message(f"**❌ Помилка**: У вас вже є активний тікет. Закрийте попередній тікет, перш ніж створити новий.", ephemeral=True)
            return

        ticket_number = len(self.tickets) + 1
        ticket_channel = await self.ticket_category.create_text_channel(f"TICKET-#{ticket_number:03d}")
        self.tickets[interaction.user.id] = ticket_channel
        overwrites = {
            interaction.guild.default_role: disnake.PermissionOverwrite(read_messages=False),
            interaction.user: disnake.PermissionOverwrite(read_messages=True, send_messages=True),
            self.mod_role: disnake.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        await ticket_channel.edit(overwrites=overwrites)
        await self.create_delete_button(ticket_channel, ticket_number, interaction.user)
        await interaction.response.send_message(f"💭 **Тікет успішно створений!** Результат можна подивитися в каналі {ticket_channel.mention}", ephemeral=True)


    async def create_delete_button(self, ticket_channel, ticket_number, user):
        embed = disnake.Embed(
            title=f"Тікет #{ticket_number}",
            color=0x007FFF,
            description=f"**Тікет успішно створений.** \nТепер, залиште повідомлення чи жалобу модераторам (або на модераторів) та чекайте відповіді. Якщо відповідь задовільна - будь ласка, закрийте тікет. Якщо відповідь модератора вас не задовольняє - згадайте адміністратора у чаті тікету. \n\n**Відправник:** {user.mention}\n**Дата створення:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        button = disnake.ui.Button(label="💥 Закрити тікет", style=disnake.ButtonStyle.danger)
        button.callback = self.close_ticket_callback
        await ticket_channel.send(embed=embed, content="", view=disnake.ui.View().add_item(button))


    async def close_ticket_callback(self, interaction):
        ticket_channel = interaction.channel
        if ticket_channel.category_id == self.ticket_category_id:
            if interaction.user.id in self.tickets:
                ticket_number = int(ticket_channel.name.split('-')[1])
                await ticket_channel.edit(name=f"{ticket_channel.name}-closed")
                del self.tickets[interaction.user.id]
                overwrites = {
                    interaction.guild.default_role: disnake.PermissionOverwrite(read_messages=False),
                    interaction.user: disnake.PermissionOverwrite(read_messages=True, send_messages=False),
                    self.mod_role: disnake.PermissionOverwrite(read_messages=True, send_messages=True)
                }
                await ticket_channel.edit(overwrites=overwrites)
                await interaction.response.send_message(f"💌 **Тікет #{ticket_number} закрито!** Сподіваємося, ви отримали задовільну відповідь від наших модераторів!", ephemeral=True)
            else:
                await interaction.response.send_message(f"**❌ Помилка**: Здається, що Ви вже закрили тікет або він не належить вам.", ephemeral=True)
        else:
            await interaction.response.send_message(f"**❌ Помилка**: Це не канал для тікету!", ephemeral=True)


def setup(bot):
    print("Loading Tickets cog...")
    bot.add_cog(TicketSystem(bot))
