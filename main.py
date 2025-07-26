import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from yt_dlp import YoutubeDL
from pytgcalls import PyTgCalls, idle
from pytgcalls.types.input_stream import InputStream
from pytgcalls.types.input_stream.quality import HighQualityAudio
from pytgcalls.types.stream import StreamAudioEnded
from config import API_ID, API_HASH, BOT_TOKEN

# Initialize Pyrogram & PyTgCalls
app = Client("MusicBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
call = PyTgCalls(app)

queue = {}

ydl_opts = {
    "format": "bestaudio",
    "outtmpl": "downloads/%(title)s.%(ext)s",
    "quiet": True,
    "nocheckcertificate": True
}
os.makedirs("downloads", exist_ok=True)

async def download_audio(query):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _download_audio, query)

def _download_audio(query):
    url = query if query.startswith("http") else f"ytsearch1:{query}"
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if "entries" in info:
            info = info["entries"][0]
        return ydl.prepare_filename(info)

async def play_next(chat_id):
    if queue.get(chat_id):
        file_path = queue[chat_id].pop(0)
        await call.join_group_call(chat_id, InputStream(file_path, HighQualityAudio()))
    else:
        await call.leave_group_call(chat_id)

@app.on_message(filters.command("play") & filters.group)
async def play(_, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: /play <song name or YouTube link>")
    query = message.text.split(maxsplit=1)[1]
    await message.reply("🔄 Downloading...")
    file_path = await download_audio(query)
    chat_id = message.chat.id

    if chat_id not in queue:
        queue[chat_id] = []
    if call.get_call(chat_id):
        queue[chat_id].append(file_path)
        return await message.reply("Added to queue!")
    queue[chat_id].append(file_path)
    await play_next(chat_id)
    await message.reply("▶ Playing!")

@app.on_message(filters.command("stop") & filters.group)
async def stop(_, message: Message):
    await call.leave_group_call(message.chat.id)
    queue.pop(message.chat.id, None)
    await message.reply("⏹ Stopped!")

@app.on_message(filters.command("skip") & filters.group)
async def skip(_, message: Message):
    await call.leave_group_call(message.chat.id)
    await play_next(message.chat.id)
    await message.reply("⏭ Skipped!")

@app.on_message(filters.command("pause") & filters.group)
async def pause(_, message: Message):
    await call.pause_stream(message.chat.id)
    await message.reply("⏸ Paused!")

@app.on_message(filters.command("resume") & filters.group)
async def resume(_, message: Message):
    await call.resume_stream(message.chat.id)
    await message.reply("▶ Resumed!")

@call.on_stream_end()
async def on_stream_end(_, update: StreamAudioEnded):
    await play_next(update.chat_id)

async def main():
    await app.start()
    await call.start()
    print("Bot started")
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
