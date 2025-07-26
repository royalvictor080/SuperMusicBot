import os
import yt_dlp
import asyncio
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.types import InlineQueryResultAudio
from pytgcalls import PyTgCalls, idle
from pytgcalls import StreamType
from pytgcalls.types import AudioPiped
from config import API_ID, API_HASH, BOT_TOKEN, MONGO_URI, FFMPEG_PATH

# ---- Setup Clients ----
app = Client("music_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
pytgcalls = PyTgCalls(app)

# ---- MongoDB ----
mongo = MongoClient(MONGO_URI)
db = mongo["musicbot"]
users_col = db["users"]

# ---- Utils ----
def log_user(user_id):
    if users_col.find_one({"user_id": user_id}) is None:
        users_col.insert_one({"user_id": user_id})

async def download_audio(query):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'outtmpl': 'song.%(ext)s',
        'quiet': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch1:{query}", download=True)
        file_name = ydl.prepare_filename(info['entries'][0])
        new_name = "song.mp3"
        os.rename(file_name, new_name)
        return new_name, info['entries'][0]['title'], info['entries'][0]['webpage_url']

# ---- Commands ----
@app.on_message(filters.command("start"))
async def start(client, message):
    log_user(message.from_user.id)
    await message.reply("🎵 **Welcome to Super Music Bot v3!**\n\n"
                        "Use `/play <song>` to stream music in voice chat.\n"
                        "Use `/song <song>` to download.\n"
                        "Use `/stats` to see user count.\n"
                        "You can also use inline: `@YourBot query`")

@app.on_message(filters.command("stats"))
async def stats(client, message):
    count = users_col.count_documents({})
    await message.reply(f"📊 **Total unique users this month:** `{count}`")

@app.on_message(filters.command("song"))
async def song(client, message):
    query = " ".join(message.command[1:])
    if not query:
        await message.reply("Usage: `/song <name>`")
        return
    await message.reply(f"🔍 Searching **{query}**...")
    file, title, url = await download_audio(query)
    await message.reply_audio(file, caption=f"[{title}]({url})", parse_mode="markdown")
    os.remove(file)

@app.on_message(filters.command("play"))
async def play(client, message):
    if len(message.command) < 2:
        await message.reply("Usage: `/play <song name>`")
        return
    query = " ".join(message.command[1:])
    await message.reply(f"🎶 Playing **{query}** in voice chat...")
    file, title, url = await download_audio(query)
    chat_id = message.chat.id
    await pytgcalls.join_group_call(
        chat_id,
        AudioPiped(file),
        stream_type=StreamType().local_stream
    )
    await message.reply(f"▶️ Now playing: [{title}]({url})", parse_mode="markdown")
    os.remove(file)

@app.on_message(filters.command("pause"))
async def pause(_, message):
    await pytgcalls.pause_stream(message.chat.id)
    await message.reply("⏸️ Paused.")

@app.on_message(filters.command("resume"))
async def resume(_, message):
    await pytgcalls.resume_stream(message.chat.id)
    await message.reply("▶️ Resumed.")

@app.on_message(filters.command("stop"))
async def stop(_, message):
    await pytgcalls.leave_group_call(message.chat.id)
    await message.reply("⏹️ Stopped streaming.")

# ---- Inline Search ----
@app.on_inline_query()
async def inline_query(client, query):
    text = query.query.strip()
    if not text:
        return
    ydl_opts = {'quiet': True, 'format': 'bestaudio'}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch3:{text}", download=False)
    results = []
    for entry in info['entries']:
        results.append(
            InlineQueryResultAudio(
                title=entry['title'],
                audio_url=entry['url'],
                caption=f"[{entry['title']}]({entry['webpage_url']})"
            )
        )
    await query.answer(results, cache_time=1)

# ---- Run Bot ----
async def main():
    await app.start()
    await pytgcalls.start()
    print("Bot is running...")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
