import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls, idle
from pytgcalls.types.input_stream import InputStream
from pytgcalls.types.input_stream.quality import HighQualityAudio
from pytgcalls.types.stream import StreamAudioEnded
from yt_dlp import YoutubeDL

# Get environment variables
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URI = os.environ.get("MONGO_URI")

# Initialize Pyrogram client and PyTgCalls
app = Client("MusicBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
pytgcalls = PyTgCalls(app)

# Download options
ydl_opts = {
    "format": "bestaudio/best",
    "outtmpl": "downloads/%(title)s.%(ext)s",
    "quiet": True
}

# Ensure downloads folder exists
os.makedirs("downloads", exist_ok=True)

async def download_audio(url):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _download_audio_sync, url)

def _download_audio_sync(url):
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
    return file_path

@app.on_message(filters.command("play") & filters.group)
async def play_song(_, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: /play <YouTube URL or search term>")

    url = message.text.split(maxsplit=1)[1]
    await message.reply("Downloading...")
    file_path = await download_audio(url)
    await message.reply("Joining VC and playing...")

    await pytgcalls.join_group_call(
        message.chat.id,
        InputStream(file_path, HighQualityAudio())
    )

@pytgcalls.on_stream_end()
async def on_stream_end(_, update: StreamAudioEnded):
    chat_id = update.chat_id
    await pytgcalls.leave_group_call(chat_id)

@app.on_message(filters.command("stop") & filters.group)
async def stop_song(_, message: Message):
    await pytgcalls.leave_group_call(message.chat.id)
    await message.reply("Stopped the music.")

async def main():
    await app.start()
    await pytgcalls.start()
    print("Music Bot is running...")
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
