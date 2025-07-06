import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv
import openai
from utils import extract_pdf_text, generate_pdf_summary, generate_audio_summary, generate_audio_by_topic, generate_complete_video
from utils_ai import generate_image_with_openai, divide_into_topics
from user_manager import UserManager

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not openai.api_key:
    print("ADVERTENCIA: OPENAI_API_KEY no está configurada en el archivo .env")
if not TELEGRAM_TOKEN:
    print("ADVERTENCIA: TELEGRAM_BOT_TOKEN no está configurada en el archivo .env")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

user_manager = UserManager()
user_states = {}


def escape_markdown(text: str) -> str:
    """Escapa caracteres especiales para Markdown de Telegram"""
    if not text:
        return text

    special_chars = ['_', '*', '[', ']',
                     '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

    escaped_text = text
    for char in special_chars:
        escaped_text = escaped_text.replace(char, f'\\{char}')

    return escaped_text


class UserState:
    def __init__(self):
        self.pdf_content = None
        self.filename = None
        self.extracted_text = None
        self.organized_topics = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /start - Mensaje de bienvenida"""
    user = update.effective_user

    user_info = user_manager.register_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code,
        is_bot=user.is_bot
    )

    user_manager.log_activity(
        user_id=user.id,
        action="bot_started",
        details={"command": "/start"}
    )

    welcome_message = f"""
🤖 **¡Hola {user.first_name or 'Usuario'}!**

Bienvenido al Bot de Resumen de PDFs

Este bot puede procesar archivos PDF y generar:
• 📄 Resúmenes en PDF
• 🎵 Audios del resumen completo
• 🎵 Audios por tema
• 🎬 Videos completos con imágenes y audio

**Cómo usar:**
1. Envía un archivo PDF
2. Elige qué tipo de resumen quieres generar
3. ¡Listo! Recibirás tu archivo procesado

**Comandos disponibles:**
/start - Mostrar este mensaje
/help - Mostrar ayuda
/status - Ver estado del procesamiento
/stats - Ver tus estadísticas
"""

    await update.message.reply_text(welcome_message, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /help - Mostrar ayuda"""
    help_message = """
📚 **Ayuda del Bot**

**Funcionalidades:**
• **PDF Resumen**: Genera un PDF con temas, imágenes y contenido organizado
• **Audio Resumen**: Crea un archivo de audio con el resumen completo
• **Audio por Tema**: Genera archivos de audio separados para cada tema
• **Video Completo**: Crea un video combinando imágenes y audios

**Proceso:**
1. Envía un archivo PDF (máximo 20MB)
2. El bot extraerá el texto y lo dividirá en temas
3. Selecciona qué tipo de resumen quieres generar
4. Espera a que se procese (puede tomar varios minutos)
5. Recibe tu archivo procesado

**Notas:**
• Los archivos se procesan uno por uno
• El bot mantiene el contenido técnico, no referencias institucionales
• Los audios se generan en español
• Los videos incluyen imágenes generadas por IA
"""

    await update.message.reply_text(help_message, parse_mode='Markdown')


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /status - Ver estado del procesamiento"""
    user_id = update.effective_user.id

    user_manager.log_activity(
        user_id=user_id,
        action="status_checked"
    )

    if user_id not in user_states:
        await update.message.reply_text("❌ No hay ningún archivo en procesamiento.")
        return

    state = user_states[user_id]
    status_message = f"""
📊 **Estado del Procesamiento**

📁 **Archivo**: {state.filename or 'No procesado'}
📝 **Texto extraído**: {'✅ Sí' if state.extracted_text else '❌ No'}
🤖 **Temas organizados**: {'✅ Sí' if state.organized_topics else '❌ No'}

**Próximo paso**: Envía un PDF para comenzar
"""

    await update.message.reply_text(status_message, parse_mode='Markdown')


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /stats - Ver estadísticas del usuario"""
    user_id = update.effective_user.id

    user_manager.log_activity(
        user_id=user_id,
        action="stats_checked"
    )

    user_stats = user_manager.get_user_stats(user_id)

    if not user_stats:
        await update.message.reply_text("❌ No se encontraron estadísticas para tu usuario.")
        return

    user_info = user_stats["user_info"]
    activity_breakdown = user_stats["activity_breakdown"]

    stats_message = f"""
📊 **Tus Estadísticas**

👤 **Usuario**: {user_info['first_name'] or 'Usuario'} {user_info['last_name'] or ''}
🆔 **ID**: `{user_info['user_id']}`
📅 **Primera vez**: {user_info['first_seen'][:10] if user_info['first_seen'] else 'N/A'}
🕐 **Última actividad**: {user_info['last_activity'][:10] if user_info['last_activity'] else 'N/A'}

📈 **Actividad Total**:
• 📁 Archivos procesados: {user_info['total_files_processed']}
• 🎯 Generaciones completadas: {user_info['total_generations']}
• 📊 Total de actividades: {user_stats['total_activities']}
• ✅ Tasa de éxito: {user_stats['success_rate']:.1%}

📋 **Desglose de Actividades**:
"""

    for action, count in activity_breakdown.items():
        action_emoji = {
            "bot_started": "🤖",
            "file_uploaded": "📁",
            "pdf_generated": "📄",
            "audio_generated": "🎵",
            "video_generated": "🎬",
            "status_checked": "📊",
            "stats_checked": "📈"
        }.get(action, "📝")

        stats_message += f"• {action_emoji} {action}: {count}\n"

    await update.message.reply_text(stats_message, parse_mode='Markdown')


async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja archivos PDF enviados por el usuario"""
    user_id = update.effective_user.id
    user = update.effective_user

    user_manager.register_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code,
        is_bot=user.is_bot
    )

    if not update.message.document or not update.message.document.file_name.lower().endswith('.pdf'):
        await update.message.reply_text("❌ Por favor, envía un archivo PDF válido.")
        user_manager.log_activity(
            user_id=user_id,
            action="invalid_file_uploaded",
            success=False,
            error_message="Archivo no es PDF"
        )
        return

    if update.message.document.file_size > 20 * 1024 * 1024:
        await update.message.reply_text("❌ El archivo es demasiado grande. Máximo 20MB permitido.")
        user_manager.log_activity(
            user_id=user_id,
            action="file_too_large",
            success=False,
            error_message="Archivo excede 20MB",
            file_processed=update.message.document.file_name
        )
        return

    processing_msg = await update.message.reply_text("🔄 Procesando PDF... Esto puede tomar unos minutos.")

    try:
        file = await context.bot.get_file(update.message.document.file_id)
        file_content = await file.download_as_bytearray()

        user_states[user_id] = UserState()
        user_states[user_id].pdf_content = file_content
        user_states[user_id].filename = update.message.document.file_name

        user_manager.start_session(
            user_id=user_id,
            filename=update.message.document.file_name,
            file_size=update.message.document.file_size
        )

        user_manager.log_activity(
            user_id=user_id,
            action="file_uploaded",
            file_processed=update.message.document.file_name,
            details={
                "file_size": update.message.document.file_size,
                "file_id": update.message.document.file_id
            }
        )

        await processing_msg.edit_text("📖 Extrayendo texto del PDF...")
        extracted_text = extract_pdf_text(file_content)

        if extracted_text.startswith("Error"):
            await processing_msg.edit_text(f"❌ Error al extraer texto: {extracted_text}")
            user_manager.log_activity(
                user_id=user_id,
                action="text_extraction_failed",
                success=False,
                error_message=extracted_text,
                file_processed=update.message.document.file_name
            )
            return

        user_states[user_id].extracted_text = extracted_text

        user_manager.update_session(
            user_id=user_id,
            extracted_text=extracted_text
        )

        await show_generation_options(update, context, processing_msg)

    except Exception as e:
        logger.error(f"Error procesando PDF: {str(e)}")
        await processing_msg.edit_text(f"❌ Error inesperado: {str(e)}")
        user_manager.log_activity(
            user_id=user_id,
            action="pdf_processing_error",
            success=False,
            error_message=str(e),
            file_processed=update.message.document.file_name if update.message.document else None
        )


async def show_generation_options(update: Update, context: ContextTypes.DEFAULT_TYPE, message: Message) -> None:
    """Muestra las opciones de generación disponibles"""
    keyboard = [
        [
            InlineKeyboardButton(
                "📄 PDF Resumen", callback_data="generate_pdf"),
            InlineKeyboardButton(
                "🎵 Audio Resumen", callback_data="generate_audio")
        ],
        [
            InlineKeyboardButton("🎵 Audio por Tema",
                                 callback_data="generate_audio_topics"),
            InlineKeyboardButton("🎬 Video Completo",
                                 callback_data="generate_video")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.edit_text(
        "✅ **PDF procesado exitosamente!**\n\n"
        f"📝 Texto extraído: {len(user_states[update.effective_user.id].extracted_text)} caracteres\n\n"
        "**¿Qué tipo de resumen quieres generar?**\n\n"
        "💡 *Nota: El procesamiento con IA se realizará cuando elijas una opción*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja los callbacks de los botones inline"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id

    if user_id not in user_states:
        await query.edit_message_text("❌ No hay ningún archivo procesado. Envía un PDF primero.")
        return

    state = user_states[user_id]

    # Mensaje de procesamiento
    processing_msg = await query.edit_message_text("🔄 Generando archivo... Esto puede tomar varios minutos.")

    try:
        if query.data == "generate_pdf":
            await generate_pdf_for_user(update, context, processing_msg, state)
        elif query.data == "generate_audio":
            await generate_audio_for_user(update, context, processing_msg, state)
        elif query.data == "generate_audio_topics":
            await generate_audio_topics_for_user(update, context, processing_msg, state)
        elif query.data == "generate_video":
            await generate_video_for_user(update, context, processing_msg, state)

    except Exception as e:
        logger.error(f"Error en callback {query.data}: {str(e)}")
        await processing_msg.edit_text(f"❌ Error generando archivo: {str(e)}")


async def generate_pdf_for_user(update: Update, context: ContextTypes.DEFAULT_TYPE, message: Message, state: UserState) -> None:
    """Genera PDF resumen para el usuario"""
    await message.edit_text("🤖 Procesando con IA para dividir en temas...")

    try:
        if not state.organized_topics:
            organized_topics = await divide_into_topics(state.extracted_text)

            if "error" in organized_topics:
                await message.edit_text(f"❌ Error al procesar con IA: {organized_topics['error']}")
                return

            state.organized_topics = organized_topics

        await message.edit_text("📄 Generando PDF resumen...")
        title = f"Resumen de {state.filename}"
        filename = f"resumen_{state.filename.replace('.pdf', '')}.pdf"

        pdf_path = generate_pdf_summary(
            title, state.organized_topics["temas"], filename)

        if pdf_path.startswith("Error"):
            await message.edit_text(f"❌ Error al generar PDF: {pdf_path}")
            return

        with open(pdf_path, 'rb') as pdf_file:
            safe_filename = escape_markdown(filename)

            topics_list = "\n".join(
                [f"• {tema['titulo']}" for tema in state.organized_topics['temas']])

            caption = f"✅ **PDF Resumen generado exitosamente!**\n\n"
            caption += f"📄 Archivo: {safe_filename}\n"
            caption += f"📊 Total de temas: {len(state.organized_topics['temas'])}\n\n"
            caption += f"**Temas incluidos:**\n{topics_list}"

            await context.bot.send_document(
                chat_id=update.effective_user.id,
                document=pdf_file,
                filename=filename,
                caption=caption,
                parse_mode='Markdown'
            )

        await message.edit_text("✅ PDF enviado exitosamente!")

    except Exception as e:
        await message.edit_text(f"❌ Error al generar PDF: {str(e)}")


async def generate_audio_for_user(update: Update, context: ContextTypes.DEFAULT_TYPE, message: Message, state: UserState) -> None:
    """Genera audio resumen para el usuario"""
    await message.edit_text("🤖 Procesando con IA para dividir en temas...")

    try:
        # Procesar con IA si no se ha hecho antes
        if not state.organized_topics:
            organized_topics = await divide_into_topics(state.extracted_text)

            if "error" in organized_topics:
                await message.edit_text(f"❌ Error al procesar con IA: {organized_topics['error']}")
                return

            state.organized_topics = organized_topics

        await message.edit_text("🎵 Generando audio resumen...")
        title = f"Resumen de {state.filename}"
        audio_filename = f"audio_resumen_{state.filename.replace('.pdf', '')}.mp3"

        audio_path = generate_audio_summary(
            title, state.organized_topics["temas"], audio_filename)

        if audio_path.startswith("Error"):
            await message.edit_text(f"❌ Error al generar audio: {audio_path}")
            return

        # Enviar archivo de audio
        with open(audio_path, 'rb') as audio_file:
            # Escapar caracteres especiales en el nombre del archivo
            safe_filename = escape_markdown(audio_filename)

            # Preparar lista de temas para mostrar
            topics_list = "\n".join(
                [f"• {tema['titulo']}" for tema in state.organized_topics['temas']])

            caption = f"✅ **Audio Resumen generado exitosamente!**\n\n"
            caption += f"🎵 Archivo: {safe_filename}\n"
            caption += f"📊 Total de temas: {len(state.organized_topics['temas'])}\n\n"
            caption += f"**Temas incluidos:**\n{topics_list}"

            await context.bot.send_audio(
                chat_id=update.effective_user.id,
                audio=audio_file,
                filename=audio_filename,
                caption=caption,
                parse_mode='Markdown'
            )

        await message.edit_text("✅ Audio enviado exitosamente!")

    except Exception as e:
        await message.edit_text(f"❌ Error al generar audio: {str(e)}")


async def generate_audio_topics_for_user(update: Update, context: ContextTypes.DEFAULT_TYPE, message: Message, state: UserState) -> None:
    """Genera audios por tema para el usuario"""
    await message.edit_text("🤖 Procesando con IA para dividir en temas...")

    try:
        # Procesar con IA si no se ha hecho antes
        if not state.organized_topics:
            organized_topics = await divide_into_topics(state.extracted_text)

            if "error" in organized_topics:
                await message.edit_text(f"❌ Error al procesar con IA: {organized_topics['error']}")
                return

            state.organized_topics = organized_topics

        await message.edit_text("🎵 Generando audios por tema...")
        base_filename = f"audio_tema_{state.filename.replace('.pdf', '')}"

        audio_files = generate_audio_by_topic(
            state.organized_topics["temas"], base_filename)

        if "error" in audio_files[0]:
            await message.edit_text(f"❌ Error al generar audios: {audio_files[0]['error']}")
            return

        # Enviar cada archivo de audio
        successful_files = 0
        for audio_file in audio_files:
            if 'archivo_audio' in audio_file:
                try:
                    with open(audio_file['archivo_audio'], 'rb') as audio:
                        # Escapar caracteres especiales en el tema
                        safe_tema = escape_markdown(audio_file['tema'])

                        await context.bot.send_audio(
                            chat_id=update.effective_user.id,
                            audio=audio,
                            filename=os.path.basename(
                                audio_file['archivo_audio']),
                            caption=f"🎵 {safe_tema}\n⏱️ Duración: {audio_file['duración_estimada']}",
                            parse_mode='Markdown'
                        )
                    successful_files += 1
                except Exception as e:
                    logger.error(
                        f"Error enviando audio {audio_file['tema']}: {str(e)}")

        # Preparar lista de temas para mostrar
        topics_list = "\n".join(
            [f"• {tema['titulo']}" for tema in state.organized_topics['temas']])

        await message.edit_text(
            f"✅ **Audios por tema generados exitosamente!**\n\n"
            f"📁 Archivos enviados: {successful_files}/{len(audio_files)}\n"
            f"📊 Total de temas: {len(state.organized_topics['temas'])}\n\n"
            f"**Temas incluidos:**\n{topics_list}"
        )

    except Exception as e:
        await message.edit_text(f"❌ Error al generar audios por tema: {str(e)}")


async def generate_video_for_user(update: Update, context: ContextTypes.DEFAULT_TYPE, message: Message, state: UserState) -> None:
    """Genera video completo para el usuario"""
    await message.edit_text("🤖 Procesando con IA para dividir en temas...")

    try:
        # Procesar con IA si no se ha hecho antes
        if not state.organized_topics:
            organized_topics = await divide_into_topics(state.extracted_text)

            if "error" in organized_topics:
                await message.edit_text(f"❌ Error al procesar con IA: {organized_topics['error']}")
                return

            state.organized_topics = organized_topics

        # Primero generar audios por tema
        await message.edit_text("🎵 Generando el audio para el video...")
        base_filename = f"video_tema_{state.filename.replace('.pdf', '')}"

        audio_files = generate_audio_by_topic(
            state.organized_topics["temas"], base_filename)

        if "error" in audio_files[0]:
            await message.edit_text(f"❌ Error al generar audios: {audio_files[0]['error']}")
            return

        # Generar video completo
        await message.edit_text("🎬 Generando video completo...")

        def send_percentage(percentage: int):
            try:
                asyncio.get_event_loop().create_task(
                    message.edit_text(
                        "❌ Error en la generación del video" if percentage == -1 else
                        "✅ Video generado exitosamente!" if percentage == 100 else
                        f"🎬 Generando video... {percentage}%"
                    )
                )
            except Exception as e:
                logger.error(f"Error actualizando progreso: {str(e)}")

        video_path = generate_complete_video(
            state.organized_topics["temas"], base_filename, send_percentage)

        if video_path.startswith("Error"):
            await message.edit_text(f"❌ Error al generar video: {video_path}")
            return

        # Enviar archivo de video
        with open(video_path, 'rb') as video_file:
            # Crear caption seguro para Markdown
            video_filename = os.path.basename(video_path)
            # Escapar caracteres especiales que pueden causar problemas en Markdown
            safe_filename = escape_markdown(video_filename)

            # Preparar lista de temas para mostrar
            topics_list = "\n".join(
                [f"• {tema['titulo']}" for tema in state.organized_topics['temas']])

            caption = f"✅ **Video Completo generado exitosamente!**\n\n"
            caption += f"🎬 Archivo: {safe_filename}\n"
            caption += f"📊 Total de temas: {len(state.organized_topics['temas'])}\n\n"
            caption += f"**Temas incluidos:**\n{topics_list}"

            await context.bot.send_video(
                chat_id=update.effective_user.id,
                video=video_file,
                filename=video_filename,
                caption=caption,
                parse_mode='Markdown'
            )

        await message.edit_text("✅ Video enviado exitosamente!")

    except Exception as e:
        await message.edit_text(f"❌ Error al generar video: {str(e)}")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja mensajes de texto"""
    await update.message.reply_text(
        "🤖 Envía un archivo PDF para comenzar a procesar.\n\n"
        "Usa /help para ver más información sobre las funcionalidades disponibles."
    )


def main() -> None:
    """Función principal del bot"""
    if not TELEGRAM_TOKEN:
        print("❌ Error: TELEGRAM_BOT_TOKEN no está configurado en el archivo .env")
        return

    # Crear aplicación
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Agregar handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("stats", stats))

    # Handler para archivos PDF
    application.add_handler(MessageHandler(filters.Document.ALL, handle_pdf))

    # Handler para callbacks de botones
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Handler para mensajes de texto
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_text))

    # Iniciar el bot
    print("🤖 Bot iniciado. Presiona Ctrl+C para detener.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
