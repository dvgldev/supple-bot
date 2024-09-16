import disnake
from disnake.ext import commands
from datetime import datetime, timedelta
import aiohttp

EVENT_TEMPLATES = {
    "chess": {
        "event_name": "Шахи ♟",
        "description": "Шахи - це гра, яка грається між двома суперниками на протилежних сторонах дошки, що містить 64 квадрати, які чергуються за кольорами. Кожен гравець має 16 фігур: 1 король, 1 ферзь, 2 тури, 2 коня, 2 слона і 8 пішаків. Мета гри полягає в тому, щоб поставити шах і мат іншому королю.",
        "rules_link": "https://uk.wikipedia.org/wiki/%D0%9F%D1%80%D0%B0%D0%B2%D0%B8%D0%BB%D0%B0_%D1%88%D0%B0%D1%85%D1%96%D0%B2",
        "cover_image": "https://media.cnn.com/api/v1/images/stellar/prod/230104173032-02-chess-stock.jpg?c=16x9&q=h_833,w_1480,c_fill"
    },
    "mafia": {
        "event_name": "Мафія 🐱‍👤",
        "description": "Мафія — це інтелектуально-психологічна покрокова рольова гра у детективному жанрі, яка моделює боротьбу організованої меншості проти неорганізованої більшості. За сюжетом мешканці міста, знесилені від розгулу мафії, приймають рішення посадити до в'язниці всіх злочинців до одного; у відповідь мафія розпочинає війну до повного знищення мирних жителів.",
        "rules_link": "https://uk.wikipedia.org/wiki/%D0%9C%D0%B0%D1%84%D1%96%D1%8F_(%D0%B3%D1%80%D0%B0)#%D0%9F%D1%80%D0%B0%D0%B2%D0%B8%D0%BB%D0%B0_%D0%B3%D1%80%D0%B8",
        "cover_image": "https://t4.ftcdn.net/jpg/06/77/76/95/360_F_677769566_H6alHNhQge3DWcZT2H4x7e44y0i0ePv1.jpg"
    }
}

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.event_channel_id = 1238540131154006089
        self.role_id = 1238819567669874710

    @commands.slash_command(name="create_event", description="Створити івент.")
    async def create_event(
        self,
        ctx,
        template_id: str = "chess",
        date_time: str = None,
    ):
        event_template = EVENT_TEMPLATES.get(template_id, EVENT_TEMPLATES["chess"])

        event_name = event_template["event_name"]
        description = event_template["description"]
        rules_link = event_template["rules_link"]
        cover_image = event_template["cover_image"]
        organizer_avatar = ctx.author.avatar.url if ctx.author.avatar else disnake.Embed.Empty
        organizer_name = ctx.author.display_name
        role_mention = ctx.guild.get_role(self.role_id).mention

        embed = disnake.Embed(title=f"{event_name}", color=0x007FFF)
        embed.description = f"```\n{description}\n```"
        embed.add_field(name="Дата та час:", value=f"{date_time}", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="Правила:", value=f"[Клік сюди]({rules_link})\n", inline=True)
        embed.set_image(url=cover_image)
        embed.set_footer(text=f"Організатор: {organizer_name}", icon_url=organizer_avatar)

        start_time = datetime.strptime(date_time, '%Y-%m-%d %H:%M')
        end_time = start_time + timedelta(hours=1)

        async with aiohttp.ClientSession() as session:
            async with session.get(cover_image) as response:
                image_data = await response.read()

        scheduled_event = await ctx.guild.create_scheduled_event(
            name=event_name,
            description=description,
            scheduled_start_time=start_time,
            scheduled_end_time=end_time,
            entity_type=disnake.GuildScheduledEventEntityType.external,
            entity_metadata=disnake.GuildScheduledEventMetadata(location=f"<#{1239168161132187740}>"),
            image=image_data
        )

        channel = self.bot.get_channel(self.event_channel_id)
        if channel:
            await channel.send(f"{role_mention}", embed=embed)
            ephemeral_message = f"✨ **Івент успішно створений!** Результат можна подивитися в каналі <#{self.event_channel_id}> та у списку запланованих подій."
            await ctx.send(ephemeral_message, ephemeral=True)
        else:
            await ctx.send("**❌ Помилка:** Не вдалося знайти канал івентів.")


def setup(bot):
    print("Loading Events cog...")
    bot.add_cog(Events(bot))
