import os
import re
import asyncio
import tempfile
import logging
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import CommandStart
from aiogram.enums import ChatAction


# ==================================
# SOZLAMALAR
# ==================================

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", "10000"))

BOT_LINK = "https://t.me/SaqlaNovaBot"
CAPTION = "📥 @SaqlaNovaBot"

MAX_FILE_SIZE = 49 * 1024 * 1024
MAX_DOWNLOADS = 2

DOWNLOAD_FOLDER = Path(tempfile.gettempdir()) / "saqlabot"
DOWNLOAD_FOLDER.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

if not TOKEN:
    raise RuntimeError(
        "BOT_TOKEN topilmadi! Render Environment Variables ni tekshiring."
    )

bot = Bot(token=TOKEN)
dp = Dispatcher()

download_semaphore = asyncio.Semaphore(MAX_DOWNLOADS)


# ==================================
# HAVOLANI TEKSHIRISH
# ==================================

ALLOWED_DOMAINS = [
    "youtube.com",
    "youtu.be",
    "instagram.com",
    "tiktok.com"
]


def is_valid_url(url):
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()

        if parsed.scheme not in ("http", "https"):
            return False

        for domain in ALLOWED_DOMAINS:
            if host == domain or host.endswith("." + domain):
                return True

        return False

    except Exception:
        return False


def find_url(text):
    if not text:
        return None

    match = re.search(r"https?://[^\s]+", text)

    if not match:
        return None

    return match.group(0).rstrip(".,!?)\"]'")


# ==================================
# VIDEO YUKLASH
# ==================================

def download_video(url, folder):

    options = {
        "format": "best[ext=mp4]/best",
        "outtmpl": str(folder / "%(title).80s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
        "socket_timeout": 30,
        "retries": 2,
        "fragment_retries": 2,
        "max_filesize": MAX_FILE_SIZE,
        "overwrites": True
    }

    with yt_dlp.YoutubeDL(options) as ydl:

        info = ydl.extract_info(url, download=True)

        if not info:
            raise Exception("Video ma'lumotini olish imkonsiz.")

        filename = ydl.prepare_filename(info)
        file_path = Path(filename)

        if not file_path.exists():

            possible_files = list(folder.glob("*"))

            if not possible_files:
                raise Exception("Yuklangan fayl topilmadi.")

            file_path = possible_files[0]

        return file_path, info.get("title", "Video")


# ==================================
# START
# ==================================

@dp.message(CommandStart())
async def start_handler(message: Message):

    await message.answer(
        "SAQLA BOT ga xush kelibsiz!\n\n"
        "Instagram, TikTok yoki YouTube havolasini yuboring.\n\n"
        "Bot videoni yuklab sizga yuboradi."
    )


# ==================================
# VIDEO QABUL QILISH
# ==================================

@dp.message(F.text)
async def video_handler(message: Message):

    url = find_url(message.text)

    if not url:

        await message.answer(
            "Iltimos, Instagram, TikTok yoki YouTube havolasini yuboring."
        )
        return

    if not is_valid_url(url):

        await message.answer(
            "Bu havola qo'llab-quvvatlanmaydi."
        )
        return

    status = await message.answer(
        "Havola qabul qilindi.\n"
        "Video yuklanmoqda..."
    )

    async with download_semaphore:

        try:

            with tempfile.TemporaryDirectory(
                dir=DOWNLOAD_FOLDER
            ) as temp_dir:

                folder = Path(temp_dir)

                file_path, title = await asyncio.to_thread(
                    download_video,
                    url,
                    folder
                )

                if not file_path.exists():

                    raise Exception("Video fayli topilmadi.")

                file_size = file_path.stat().st_size

                if file_size > MAX_FILE_SIZE:

                    await status.edit_text(
                        "Video hajmi 49 MB dan katta."
                    )
                    return

                await status.edit_text(
                    "Video tayyor!\n"
                    "Telegramga yuborilmoqda..."
                )

                if file_path.suffix.lower() == ".mp4":

                    video = FSInputFile(
                        path=str(file_path),
                        filename="SAQLA_BOT.mp4"
                    )

                    await message.answer_video(
                        video=video,
                        caption=CAPTION
                    )

                else:

                    document = FSInputFile(
                        path=str(file_path)
                    )

                    await message.answer_document(
                        document=document,
                        caption=CAPTION
                    )

                await status.delete()

        except Exception as error:

            logger.exception("Video yuklashda xatolik")

            error_text = str(error)

            if len(error_text) > 300:
                error_text = error_text[:300]

            try:

                await status.edit_text(
                    "Videoni yuklashda xatolik yuz berdi.\n\n"
                    "Sabab: " + error_text
                )

            except Exception:

                await message.answer(
                    "Videoni yuklashda xatolik yuz berdi."
                )


# ==================================
# RENDER HEALTH SERVER
# ==================================

async def health_server():

    async def handle_client(reader, writer):

        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/plain\r\n"
            "Content-Length: 16\r\n"
            "Connection: close\r\n"
            "\r\n"
            "SAQLA BOT ACTIVE"
        )

        writer.write(response.encode("utf-8"))
        await writer.drain()

        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(
        handle_client,
        "0.0.0.0",
        PORT
    )

    logger.info(
        "Health server PORT %s da ishga tushdi",
        PORT
    )

    async with server:
        await server.serve_forever()


# ==================================
# BOTNI ISHGA TUSHIRISH
# ==================================

async def main():

    logger.info("SAQLA BOT ishga tushmoqda...")

    await asyncio.gather(
        dp.start_polling(bot),
        health_server()
    )


if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        logger.info("Bot to'xtatildi.")
