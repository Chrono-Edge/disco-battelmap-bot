import asyncio
import io
from pickle import FALSE
from typing import Optional
from config import values
import aiohttp
import interactions
from interactions import slash_command, SlashContext
from interactions import OptionType, slash_option, Attachment
from utils import board
from config import logger

bot = interactions.Client(
    sync_interactions=True,
)

storage = {

}


@slash_command(name="start_session", description="Start new map")
@slash_option(
    name="map_image",
    description="Setup you custom map image",
    required=True,
    opt_type=OptionType.ATTACHMENT
)
@slash_option(
    name="square_size",
    description="Setup you custom square image",
    required=False,
    opt_type=OptionType.INTEGER
)
async def start_session(ctx: SlashContext, map_image: Attachment, square_size: int = 70):
    await ctx.defer()

    aiohttp_session = aiohttp.ClientSession()
    async with aiohttp_session.get(map_image.url) as resp:
        image_bytes = await resp.content.read()
    await aiohttp_session.close()
    logger.info("Start load board")
    current_board = board.Board(image_bytes, cell_size=square_size)
    logger.info("Render image")
    image = current_board.draw()
    file_out = io.BytesIO()
    image.format = "webp"
    image.save(file=file_out)
    file_out.seek(0)

    file_a = interactions.File(file_out, "image.webp")
    logger.info("send image")
    await ctx.send(file=file_a)

    logger.info("Render image2")
    image = current_board.draw()
    file_out = io.BytesIO()
    image.format = "webp"
    image.save(file=file_out)
    file_out.seek(0)

    file_a = interactions.File(file_out, "image.webp")
    logger.info("send image2")
    await ctx.send(file=file_a)


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


bot.start(values.get("secrets.token"))
