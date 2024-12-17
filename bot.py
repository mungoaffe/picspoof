import os
import random
from PIL import Image, ImageEnhance
import piexif
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
import tempfile

# Dein Bot-Token hier einfügen
TELEGRAM_BOT_TOKEN = '7774391850:AAGzHbtELHP1XSPgbS3XncNfBDMrySMEgEQ'

# Liste der erlaubten Nutzer-IDs
ALLOWED_USERS = [2028801909, 8143592902]

# Zustände des ConversationHandlers
REPEAT_COUNT, PHOTO = range(2)

def start_keyboard():
    keyboard = [[InlineKeyboardButton("Start", callback_data='start')]]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text(f"ask for permission with ur id: {user_id}")
        return ConversationHandler.END

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("type the number of pictures u need. If something not works -> /cancel")
    else:
        await update.message.reply_text("type the number of pictures u need. If something not works -> /cancel")
    return REPEAT_COUNT

async def get_repeat_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("ask for permission")
        return ConversationHandler.END

    try:
        repeat_count = int(update.message.text)
        context.user_data['repeat_count'] = repeat_count
        context.user_data['photos'] = []  # Initialisiere eine Liste für Fotos
        await update.message.reply_text(f"now send me the pictures")
        return PHOTO
    except ValueError:
        await update.message.reply_text("send a number")
        return REPEAT_COUNT

def deg_to_dms(deg):
    d = int(deg)
    m = int((deg - d) * 60)
    s = (deg - d - m / 60) * 3600
    return [(d, 1), (m, 1), (int(s * 100), 100)]

import piexif
from PIL import Image

def process_image(image, repeat_count):
    def random_us_coordinates():
        lat = random.uniform(24.396308, 49.384358)  # Zufällige US-Breitengrad-Koordinaten
        lon = random.uniform(-125.0, -66.93457)    # Zufällige US-Längengrad-Koordinaten
        return lat, lon

    images = []
    for i in range(repeat_count):
        img = image.copy()

        # Helligkeit anpassen
        brightness_factor = random.uniform(0.94, 1.06)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(brightness_factor)

        # Kontrast anpassen
        contrast_factor = random.uniform(0.94, 1.06)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contrast_factor)

        # Schärfe anpassen
        sharpness_factor = random.uniform(0.94, 1.06)
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(sharpness_factor)

        # Zufällige Änderung der Bildgröße
        max_pixel_change = 10
        pixel_change = random.randint(0, max_pixel_change)
        new_width = img.width - pixel_change
        new_height = img.height - pixel_change
        new_width = max(1, new_width)
        new_height = max(1, new_height)
        img = img.resize((new_width, new_height), Image.LANCZOS)

        # Berechne 0,5% des Randes des Bildes
        border_percentage_max = 0.01  # Maximal
        border_percentage = random.uniform(0, border_percentage_max)  

        # Berechne die Schnittpunkte für den Rand
        left = int(img.width * border_percentage)
        top = int(img.height * border_percentage)
        right = img.width - left
        bottom = img.height - top

        # Stelle sicher, dass die rechte Grenze immer größer ist als die linke
        if right <= left:
            right = img.width
        if bottom <= top:
            bottom = img.height

        # Schneide den Rand ab
        img = img.crop((left, top, right, bottom))

        # Farbkorrektur
        color_factor = random.uniform(0.94, 1.06)
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(color_factor)

        # Rotation des Bildes
        rotation_angle = random.uniform(-0.05, 0.05)
        img = img.rotate(rotation_angle, expand=True)

        # Zufälliges Spiegeln des Bildes
        if random.choice([True, False]):
            img = img.transpose(Image.FLIP_LEFT_RIGHT)

        try:
            exif_dict = piexif.load(img.info.get("exif", b""))
        except Exception:
            exif_dict = {"Exif": {}, "GPS": {}}

        # Behalte nur die GPS-Daten und lösche alle anderen EXIF-Daten
        exif_dict["Exif"] = {}  # Entfernt alle EXIF-Metadaten wie Kamera, Uhrzeit, etc.
        
        # Generiere zufällige GPS-Koordinaten
        lat, lon = random_us_coordinates()
        lat_ref = "N" if lat >= 0 else "S"
        lon_ref = "E" if lon >= 0 else "W"

        exif_dict["GPS"] = {
            piexif.GPSIFD.GPSLatitude: deg_to_dms(abs(lat)),
            piexif.GPSIFD.GPSLatitudeRef: lat_ref,
            piexif.GPSIFD.GPSLongitude: deg_to_dms(abs(lon)),
            piexif.GPSIFD.GPSLongitudeRef: lon_ref
        }

        # Speichere die EXIF-Daten in die Bilddatei
        new_exif_data = piexif.dump(exif_dict)
        with tempfile.NamedTemporaryFile(suffix='.jpeg', delete=False) as temp_file:
            img.save(temp_file, "jpeg", exif=new_exif_data, quality=95)  # Speichert mit den neuen EXIF-Daten
            images.append(temp_file.name)

    return images

import os

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("ask for permission")
        return ConversationHandler.END

    photo_file = await update.message.photo[-1].get_file()
    with tempfile.NamedTemporaryFile(suffix='.jpeg', delete=False) as temp_file:
        await photo_file.download_to_drive(temp_file.name)
        context.user_data['photos'].append(temp_file.name)  # Foto zur Warteschlange hinzufügen

    if len(context.user_data['photos']) > 1:
        return PHOTO  # Warte auf weitere Bilder

    edited_images = []
    while context.user_data['photos']:
        photo_path = context.user_data['photos'].pop(0)  # Bearbeite das erste Foto
        with Image.open(photo_path) as img:
            repeat_count = context.user_data.get('repeat_count', 1)
            edited_images.extend(process_image(img, repeat_count))  # Bilder zur Liste hinzufügen

    # Teile die bearbeiteten Bilder in Gruppen zu je maximal 10
    for i in range(0, len(edited_images), 10):  # max 10 Bilder pro Gruppe
        media_group_chunk = edited_images[i:i + 10]  # Erstelle eine Gruppe von bis zu 10 Bildern
        media = [InputMediaPhoto(media=open(image, 'rb')) for image in media_group_chunk]
        
        # Sende das Media-Gruppe
        await update.message.reply_media_group(media=media)

    await update.message.reply_text("done. restart with /start.")

    # Lösche die temporären Bilder, nachdem sie gesendet wurden
    for photo_path in context.user_data['photos']:
        try:
            os.remove(photo_path)  # Löscht die temporären Bilddateien
        except Exception as e:
            print(f"Fehler beim Löschen der Datei {photo_path}: {e}")

    # Lösche auch die bearbeiteten Bilder
    for edited_image in edited_images:
        try:
            os.remove(edited_image)  # Löscht die bearbeiteten temporären Bilddateien
        except Exception as e:
            print(f"Fehler beim Löschen der bearbeiteten Datei {edited_image}: {e}")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("ask for permission")
        return ConversationHandler.END

    await update.message.reply_text("abort mission. restart with /start.")
    return ConversationHandler.END

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            REPEAT_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_repeat_count)],
            PHOTO: [MessageHandler(filters.PHOTO, handle_photo)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(start, pattern='start'))

    application.run_polling()

if __name__ == "__main__":
    main()
