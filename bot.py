import os
import random
from PIL import Image, ImageEnhance
import piexif
from telegram import Update, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
import tempfile

# Dein Bot-Token hier einfügen
TELEGRAM_BOT_TOKEN = '7774391850:AAGzHbtELHP1XSPgbS3XncNfBDMrySMEgEQ'

# Liste der erlaubten Nutzer-IDs
ALLOWED_USERS = [2028801909, 8143592902, 5415872566]

# Zustände des ConversationHandlers
REPEAT_COUNT, PHOTO = range(2)

def start_keyboard():
    keyboard = [[InlineKeyboardButton("Start", callback_data='start')]]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text(f"ask for permission with your id: {user_id}")
        return ConversationHandler.END

    await update.message.reply_text("type the number of pictures you need. If something doesn't work -> /cancel")
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
        context.user_data['notified'] = False  # Notification-Flag
        await update.message.reply_text("Now send me the pictures")
        return PHOTO
    except ValueError:
        await update.message.reply_text("Please send a valid number")
        return REPEAT_COUNT

def deg_to_dms(deg):
    d = int(deg)
    m = int((deg - d) * 60)
    s = (deg - d - m / 60) * 3600
    return [(d, 1), (m, 1), (int(s * 100), 100)]

def process_image(image, repeat_count):
    def random_us_coordinates():
        lat = random.uniform(24.396308, 49.384358)
        lon = random.uniform(-125.0, -66.93457)
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

        # Zufällige GPS-Daten generieren
        lat, lon = random_us_coordinates()
        lat_ref = "N" if lat >= 0 else "S"
        lon_ref = "E" if lon >= 0 else "W"

        exif_dict["GPS"] = {
            piexif.GPSIFD.GPSLatitude: deg_to_dms(abs(lat)),
            piexif.GPSIFD.GPSLatitudeRef: lat_ref,
            piexif.GPSIFD.GPSLongitude: deg_to_dms(abs(lon)),
            piexif.GPSIFD.GPSLongitudeRef: lon_ref
        }

        new_exif_data = piexif.dump(exif_dict)
        with tempfile.NamedTemporaryFile(suffix='.jpeg', delete=False) as temp_file:
            img.save(temp_file, "jpeg", exif=new_exif_data, quality=95)
            images.append(temp_file.name)

    return images

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("ask for permission")
        return ConversationHandler.END

    photo_file = await update.message.photo[-1].get_file()
    with tempfile.NamedTemporaryFile(suffix='.jpeg', delete=False) as temp_file:
        await photo_file.download_to_drive(temp_file.name)
        context.user_data.setdefault('photos', []).append(temp_file.name)

    if not context.user_data.get('notified', False):
        await update.message.reply_text("Photo received. Send more or type /process to start processing.")
        context.user_data['notified'] = True  # Setze das Flag, um Mehrfachbenachrichtigungen zu vermeiden
    return PHOTO

async def process_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("ask for permission")
        return ConversationHandler.END

    photos = context.user_data.get('photos', [])
    repeat_count = context.user_data.get('repeat_count', 1)

    if not photos:
        await update.message.reply_text("No photos to process. Please upload photos first.")
        return ConversationHandler.END

    edited_images = []
    for photo_path in photos:
        with Image.open(photo_path) as img:
            edited_images.extend(process_image(img, repeat_count))

    for i in range(0, len(edited_images), 10):
        media_group_chunk = edited_images[i:i + 10]
        media = [InputMediaPhoto(media=open(image, 'rb')) for image in media_group_chunk]
        await update.message.reply_media_group(media=media)

    await update.message.reply_text("Processing complete.")

    # Bereinigen
    for path in photos + edited_images:
        try:
            os.remove(path)
        except Exception as e:
            print(f"Error deleting file {path}: {e}")

    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("ask for permission")
        return ConversationHandler.END

    await update.message.reply_text("Operation cancelled. Restart with /start.")
    return ConversationHandler.END

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            REPEAT_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_repeat_count)],
            PHOTO: [MessageHandler(filters.PHOTO, handle_photo), CommandHandler('process', process_photos)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
