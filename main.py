import asyncio
from typing import Optional
from config import values
import aiohttp
import interactions
from interactions import slash_command, SlashContext
from interactions import OptionType, slash_option, Attachment
from utils import board

bot = interactions.Client(
    sync_interactions=True,
)


@slash_command(name="start_session", description="Start new map")
@slash_option(
    name="Map Image",
    description="Setup you custom map image",
    required=True,
    opt_type=OptionType.ATTACHMENT
)
@slash_option(
    name="square size",
    description="Setup you custom square image",
    required=True,
    opt_type=OptionType.INTEGER
)
async def start_session(ctx: SlashContext, image: Attachment):
    await ctx.defer()

    await ctx.send(f"{image.url}")


@slash_command(name="my_command", description="My first command :)")
async def my_command_function(ctx: SlashContext):
    await ctx.defer()
    await ctx.send("Hello World")


@slash_command(name="my_long_command", description="My second command :)")
async def my_long_command_function(ctx: SlashContext):
    # need to defer it, otherwise, it fails
    await ctx.defer()

    # do stuff for a bit
    await asyncio.sleep(600)

    await ctx.send("Hello World")


@interactions.listen()
async def on_startup():
    print("Bot is ready!")


bot.start(values.get("bot.token"))
