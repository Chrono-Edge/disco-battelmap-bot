import discord
from discord.ext import commands

# Use global values with custom class as state
# Drop all logs of battle a

# Создаем бота с базовыми intents
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Класс View для нашего меню с кнопками
class MenuView(discord.ui.View):
    def __init__(self):
        super().__init__()

    # Кнопка 1
    @discord.ui.button(label="Опция 1", style=discord.ButtonStyle.primary, custom_id="option1")
    async def option1(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_message("Вы выбрали опцию 1", ephemeral=True)

    # Кнопка 2
    @discord.ui.button(label="Опция 2", style=discord.ButtonStyle.secondary, custom_id="option2")
    async def option2(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_message("Вы выбрали опцию 2", ephemeral=True)

# Команда для вызова меню
@bot.command()
async def menu(ctx):
    view = MenuView()
    await ctx.send("Выберите опцию:", view=view)

bot.run("YOUR_BOT_TOKEN")
