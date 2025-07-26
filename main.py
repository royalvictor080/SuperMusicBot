import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls, idle
from pytgcalls.types.input_stream import InputStream
from pytgcalls.types.input_stream.quality import HighQualityAudio
from pytgcalls.types.stream import StreamAudioEnded
from yt_dlp import YoutubeDL

# Environment variables
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Pyrogram Client
app = Client("MusicBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
pytgcalls = PyTgCalls(app)

# YoutubeDL options
ydl_opts = {
    "format": "bestaudio/best",
    "outtmpl": "downloads/%(title)s.%(ext)s",
    "quiet": True,
    "nocheckcertificate": True
}

os.makedirs("downloads", exist_ok=True)

async def download_audio(query: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _download_audio_sync, query)

def _download_audio_sync(query: str) -> str:
    url = query
    if not query.startswith("http"):
        url = f"ytsearch1:{query}"
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if "entries" in info:
            info = info["entries"][0]
        return ydl.prepare_filename(info)

@app.on_message(filters.command("play") & filters.group)
async def play_handler(_, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: `/play <YouTube URL or song name>`")

    query = message.text.split(maxsplit=1)[1]
    await message.reply("🔄 Downloading audio...")
    file_path = await download_audio(query)
    await message.reply("▶ Playing in voice chat...")

    await pytgcalls.join_group_call(
        message.chat.id,
        InputStream(file_path, HighQualityAudio())
    )

@app.on_message(filters.command("stop") & filters.group)
async def stop_handler(_, message: Message):
    await pytgcalls.leave_group_call(message.chat.id)
    await message.reply("⏹ Stopped the music.")

@pytgcalls.on_stream_end()
async def stream_end_handler(_, update: StreamAudioEnded):
    chat_id = update.chat_id
    await pytgcalls.leave_group_call(chat_id)

async def main():
    await app.start()
    await pytgcalls.start()
    print("Music bot is running...")
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
