import os
import asyncio
from aiogram import Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.database import get_user_language, set_user_language, get_stats, increment_download
from app.database.connection import async_session
from app.i18n import get_text
from app.downloader import extract_media_info, download_video_format
from app.music_recognizer import recognize_audio

router = Router()

def get_lang_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="setlang_uz"),
         InlineKeyboardButton(text="🇷🇺 Русский", callback_data="setlang_ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="setlang_en")]
    ])

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    async with async_session() as session:
        lang = await get_user_language(session, message.from_user.id)
    
    if not lang:
        await message.answer(get_text("uz", "select_language"), reply_markup=get_lang_keyboard())
    else:
        await message.answer(get_text(lang, "welcome"))

@router.callback_query(F.data.startswith("setlang_"))
async def process_language_choice(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    
    async with async_session() as session:
        await set_user_language(
            session=session,
            telegram_id=callback.from_user.id,
            username=callback.from_user.username or "",
            first_name=callback.from_user.first_name or "",
            language=lang
        )
        
    await callback.message.edit_text(get_text(lang, "lang_changed"))
    await callback.message.answer(get_text(lang, "welcome"))

@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    async with async_session() as session:
        lang = (await get_user_language(session, message.from_user.id)) or "uz"
        users, downloads = await get_stats(session)
        
    await message.answer(get_text(lang, "stats", users=users, downloads=downloads))

@router.message(Command("settings"))
async def cmd_settings(message: types.Message):
    async with async_session() as session:
        lang = (await get_user_language(session, message.from_user.id)) or "uz"
        
    await message.answer(get_text(lang, "select_language"), reply_markup=get_lang_keyboard())

# URL qabul qilish va Video sifatini tanlash
@router.message(F.text.startswith("http://") | F.text.startswith("https://"))
async def handle_url(message: types.Message):
    async with async_session() as session:
        lang = (await get_user_language(session, message.from_user.id)) or "uz"
        
    status_msg = await message.answer(get_text(lang, "downloading"))
    
    try:
        url = message.text.strip()
        info = await extract_media_info(url) if asyncio.iscoroutinefunction(extract_media_info) else extract_media_info(url)
        
        buttons = []
        for fmt in info.get('formats', []):
            btn_text = f"🎬 {fmt['resolution']} ({fmt['filesize_mb']} MB)"
            buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"dlfmt|{fmt['format_id']}")])
        
        if not buttons:
            buttons.append([InlineKeyboardButton(text="🎬 Standard Video", callback_data="dlfmt|best")])
            
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await status_msg.edit_text(
            get_text(lang, "select_format", title=info.get('title', ''), duration=info.get('duration', '')),
            reply_markup=markup
        )
    except Exception as e:
        await status_msg.edit_text(get_text(lang, "error_occurred"))

# Tanlangan format bo'yicha videoni yuklash
@router.callback_query(F.data.startswith("dlfmt|"))
async def process_format_download(callback: types.CallbackQuery):
    async with async_session() as session:
        lang = (await get_user_language(session, callback.from_user.id)) or "uz"
        await increment_download(session, callback.from_user.id)
        
    format_id = callback.data.split("|")[1]
    await callback.message.edit_text(get_text(lang, "downloading_format"))
    
    try:
        music_btn = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(lang, "btn_download_music"), callback_data="get_music")]
        ])
        
        await callback.message.answer("🎬 Video tayyor!", reply_markup=music_btn)
    except Exception as e:
        await callback.message.answer(get_text(lang, "error_occurred"))

# Voice Message orqali Musiqa Aniqlash
@router.message(F.voice)
async def handle_voice(message: types.Message, bot):
    async with async_session() as session:
        lang = (await get_user_language(session, message.from_user.id)) or "uz"
        
    status_msg = await message.answer(get_text(lang, "recognizing_music"))
    
    file_info = await bot.get_file(message.voice.file_id)
    temp_voice_path = f"voice_{message.voice.file_id}.ogg"
    await bot.download_file(file_info.file_path, temp_voice_path)
    
    result = await recognize_audio(temp_voice_path)
    
    if os.path.exists(temp_voice_path):
        os.remove(temp_voice_path)
        
    if result:
        text = get_text(
            lang, "music_found",
            artist=result.get('artist', ''),
            title=result.get('title', ''),
            album=result.get('album', ''),
            year=result.get('release_date', ''),
            confidence=result.get('score', '')
        )
        await status_msg.edit_text(text)
    else:
        await status_msg.edit_text(get_text(lang, "music_not_found"))