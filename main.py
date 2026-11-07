import os
import re
import asyncio
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message

==============================

SAQLA BOT CONFIGURATION

==============================

TOKEN = os.getenv(“BOT_TOKEN”)
PORT = int(os.getenv(“PORT”, “10000”))

MAX_SIZE = 49 * 1024 * 1024
MAX_CONCURRENT_DOWNLOADS = 3

if not TOKEN:
raise RuntimeError(“BOT_TOKEN topilmadi!”)

bot = Bot(token=TOKEN)
dp = Dispatcher()

download_limit = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)

ALLOWED_DOMAINS = {
“instagram.com”,
“www.instagram.com”,
“tiktok.com”,
“www.tiktok.com”,
“vm.tiktok.com”,
“youtube.com”,
“www.youtube.com”,
“m.youtube.com”,
“youtu.be”,
}

==============================

LINK VALIDATION

==============================

def get_video_link(text):

match = re.search(r"https?://[^\s]+", text)
if not match:
    return None
url = match.group(0).rstrip(".,!?)\"]}")
try:
    parsed = urlparse(url)
    domain = parsed.hostname
    if not domain:
        return None
    domain = domain.lower()
    if domain not in ALLOWED_DOMAINS:
        return None
    return url
except Exception:
    return None

==============================

VIDEO DOWNLOADER

==============================

def download_video(url, folder):

output = os.path.join(folder, "video.%(ext)s")
options = {
    "format": "best[filesize<49M]/best",
    "outtmpl": output,
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "socket_timeout": 20,
    "retries": 2,
    "fragment_retries": 2,
    "max_filesize": MAX_SIZE,
    "merge_output_format": "mp4",
}
with yt_dlp.YoutubeDL(options) as downloader:
    downloader.download([url])
files = [
    file for file in Path(folder).glob("video.*")
    if file.is_file()
]
if not files:
    raise Exception("Video topilmadi")
video = max(files, key=lambda file: file.stat().st_size)
if video.stat().st_size > MAX_SIZE:
    raise Exception("Video hajmi juda katta")
return video

==============================

START COMMAND

==============================

@dp.message(CommandStart())
async def start(message: Message):

await message.answer(
    "🎬 SAQLA BOT\n"
    "━━━━━━━━━━━━━━━━\n\n"
    "Videolarni tez va oson saqlang!\n\n"
    "📥 Instagram\n"
    "📥 TikTok\n"
    "📥 YouTube\n\n"
    "Havolani yuboring — bot videoni "
    "avtomatik tayyorlaydi.\n\n"
    "⚡ SAQLA — tezkor video yuklash."
)

==============================

VIDEO PROCESSING

==============================

@dp.message(F.text)
async def receive_link(message: Message):

url = get_video_link(message.text)
if not url:
    await message.answer(
        "🔗 Iltimos, Instagram, TikTok "
        "yoki YouTube havolasini yuboring."
    )
    return
status = await message.answer(
    "⏳ Video qabul qilindi.\n"
    "Yuklash boshlanmoqda..."
)
async with download_limit:
    try:
        with tempfile.TemporaryDirectory() as folder:
            loop = asyncio.get_running_loop()
            video = await loop.run_in_executor(
                None,
                download_video,
                url,
                folder
            )
            await status.edit_text(
                "📤 Video tayyor!\n"
                "Telegramga yuborilmoqda..."
            )
            with open(video, "rb") as file:
                await message.answer_video(
                    video=file,
                    caption="✅ SAQLA BOT"
                )
            await status.delete()
    except Exception as error:
        print("DOWNLOAD ERROR:", repr(error))
        await status.edit_text(
            "❌ Videoni yuklash amalga oshmadi.\n\n"
            "Sabablari:\n"
            "• Havola ishlamayapti.\n"
            "• Video yopiq yoki mavjud emas.\n"
            "• Platforma yuklashga ruxsat bermadi.\n"
            "• Video hajmi juda katta.\n\n"
            "Boshqa havola bilan urinib ko‘ring."
        )

==============================

RENDER HEALTH SERVER

==============================

async def handle_http(reader, writer):

try:
    await reader.read(1024)
    response = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/plain\r\n"
        "Content-Length: 16\r\n"
        "Connection: close\r\n"
        "\r\n"
        "SAQLA BOT ACTIVE"
    )
    writer.write(response.encode())
    await writer.drain()
finally:
    writer.close()
    await writer.wait_closed()

==============================

MAIN

==============================

async def main():

server = await asyncio.start_server(
    handle_http,
    "0.0.0.0",
    PORT
)
print("━━━━━━━━━━━━━━━━━━━━")
print("SAQLA BOT IS RUNNING")
print("HTTP SERVER:", PORT)
print("DOWNLOAD ENGINE: READY")
print("━━━━━━━━━━━━━━━━━━━━")
async with server:
    await asyncio.gather(
        dp.start_polling(bot),
        server.serve_forever()
    )

if name == “main”:

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("SAQLA BOT STOPPED")
