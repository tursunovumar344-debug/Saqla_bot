import os
import re
import asyncio
import tempfile
from pathlib import Path

import yt_dlp
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

DOWNLOAD_LIMIT = asyncio.Semaphore(3)
MAX_SIZE = 49 * 1024 * 1024

PLATFORMS = (
    "instagram.com",
    "tiktok.com",
    "youtube.com",
    "youtu.be"
)


def valid_link(text):
    match = re.search(r"https?://\S+", text)

    if not match:
        return None

    url = match.group(0).rstrip(".,)")
    if any(site in url.lower() for site in PLATFORMS):
        return url

    return None


def download_video(url, folder):
    options = {
        "format": "best[ext=mp4]/best",
        "outtmpl": f"{folder}/video.%(ext)s",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "max_filesize": MAX_SIZE,
        "socket_timeout": 20,
        "retries": 2,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([url])

    files = list(Path(folder).glob("video.*"))

    if not files:
        raise Exception("Video topilmadi")

    return files[0]


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🎬 SAQLA BOT\n\n"
        "Videoni saqlash endi oson!\n\n"
        "Instagram, TikTok yoki YouTube "
        "havolasini yuboring.\n\n"
        "📥 Bot videoni avtomatik yuklaydi."
    )


@dp.message(F.text)
async def receive_link(message: Message):
    url = valid_link(message.text)

    if not url:
        await message.answer(
            "⚠️ Iltimos, Instagram, TikTok yoki "
            "YouTube havolasini yuboring."
        )
        return

    status = await message.answer("⏳ Video tayyorlanmoqda...")

    async with DOWNLOAD_LIMIT:
        try:
            with tempfile.TemporaryDirectory() as folder:
                loop = asyncio.get_running_loop()

                video = await loop.run_in_executor(
                    None,
                    download_video,
                    url,
                    folder
                )

                if video.stat().st_size > MAX_SIZE:
                    await status.edit_text(
                        "⚠️ Video Telegram orqali yuborish "
                        "uchun juda katta."
                    )
                    return

                await status.edit_text("📤 Video yuborilmoqda...")

                with video.open("rb") as file:
                    await message.answer_video(
                        video=file,
                        caption="✅ SAQLA BOT"
                    )

                await status.delete()

        except Exception:
            await status.edit_text(
                "❌ Videoni yuklash amalga oshmadi.\n"
                "Havolani tekshirib, qayta urinib ko‘ring."
            )


async def main():
    print("SAQLA BOT ishga tushdi!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
