import io
import os
import shutil
import tempfile
import uuid
from datetime import datetime
from typing import Optional

import PyPDF2
import requests
from gtts import gTTS
from moviepy.editor import (AudioFileClip, CompositeVideoClip, ImageClip,
                            VideoFileClip, concatenate_videoclips)
from PIL import Image as PILImage
from pydub import AudioSegment
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer)

os.environ["IMAGEIO_FFMPEG_EXE"] = os.path.join(
    os.path.dirname(__file__), "ffmpeg_bin", "ffmpeg")

# Configurar pydub para usar ffmpeg local
ffmpeg_path = os.path.join(os.path.dirname(__file__), "ffmpeg_bin", "ffmpeg")
AudioSegment.converter = ffmpeg_path
AudioSegment.ffmpeg = ffmpeg_path


def extract_pdf_text(content: bytes, work_directory: Optional[str] = None) -> str:
    """Extrae el texto de un archivo PDF a partir de su contenido en bytes."""
    try:
        pdf_file = io.BytesIO(content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""

        if len(pdf_reader.pages) == 0:
            return "Error al extraer texto: El PDF no contiene páginas"

        for page_num, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                else:
                    print(
                        f"⚠️  Página {page_num + 1} no contiene texto extraíble")
            except Exception as e:
                print(
                    f"⚠️  Error extrayendo texto de página {page_num + 1}: {str(e)}")
                continue

        extracted_text = text.strip()

        # Usar directorio proporcionado o crear uno nuevo
        if not work_directory:
            work_directory = create_work_directory()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_text_filename = os.path.join(
            work_directory, f"texto_raw_{timestamp}.txt")

        try:
            with open(raw_text_filename, 'w', encoding='utf-8') as f:
                f.write(extracted_text)
            print(f"🔍 Texto raw guardado para debug en: {raw_text_filename}")
            print(
                f"📝 Longitud del texto raw: {len(extracted_text)} caracteres")
            print(f"📄 Páginas procesadas: {len(pdf_reader.pages)}")

        except Exception as e:
            print(f"⚠️  Error al guardar texto raw: {str(e)}")

        if not extracted_text or len(extracted_text) < 10:
            return "Error al extraer texto: El PDF no contiene texto legible o está vacío"

        readable_chars = sum(
            1 for c in extracted_text if c.isalnum() or c.isspace())
        if readable_chars < len(extracted_text) * 0.3:
            return "Error al extraer texto: El texto extraído parece estar corrupto o no es legible"

        suspicious_patterns = [
            '/0', '/1', '/2', '/3', '/4', '/5', '/6', '/7', '/8', '/9',
            '□', '■', '▢', '▣', '▤', '▥', '▦', '▧', '▨', '▩',
            '\\0', '\\1', '\\2', '\\3', '\\4', '\\5', '\\6', '\\7', '\\8', '\\9'
        ]

        suspicious_count = 0
        for pattern in suspicious_patterns:
            suspicious_count += extracted_text.count(pattern)

        if suspicious_count > len(extracted_text) * 0.1:
            return f"Error al extraer texto: El texto contiene demasiados caracteres sospechosos ({suspicious_count} encontrados). El PDF puede estar corrupto o no ser legible."

        words = extracted_text.split()
        real_words = [word for word in words if len(
            word) >= 3 and any(c.isalpha() for c in word)]
        if len(real_words) < 5:
            return "Error al extraer texto: El texto no contiene suficientes palabras legibles"

        text_filename = os.path.join(
            work_directory, f"texto_extraido_{timestamp}.txt")

        try:
            with open(text_filename, 'w', encoding='utf-8') as f:
                f.write(extracted_text)
            print(f"💾 Texto extraído guardado en: {text_filename}")
            print(f"📝 Longitud del texto: {len(extracted_text)} caracteres")
            print(f"📄 Páginas procesadas: {len(pdf_reader.pages)}")
            print(f"🔍 Palabras legibles encontradas: {len(real_words)}")

        except Exception as e:
            print(f"⚠️  Error al guardar texto extraído: {str(e)}")

        return extracted_text

    except Exception as e:
        error_msg = f"Error al extraer texto: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg


def download_image(url: str, filename: str) -> str:
    """Descarga una imagen desde una URL y la guarda localmente."""
    try:
        print(f"📥 Descargando imagen: {url}")
        response = requests.get(url)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"✅ Imagen descargada: {filename}")
            return filename
        else:
            print(f"❌ Error al descargar imagen: {response.status_code}")
            return ""
    except Exception as e:
        print(f"❌ Error al descargar imagen: {str(e)}")
        return ""


def create_topic_video(image_path: str, audio_path: str, title: str, output_path: str) -> str:
    """Crea un video para un tema específico combinando imagen y audio."""
    try:
        with PILImage.open(image_path) as img:
            img = img.resize((1280, 720))
            temp_img_path = tempfile.mktemp(suffix='.png')
            img.save(temp_img_path)

        image_clip = ImageClip(temp_img_path).set_duration(
            AudioFileClip(audio_path).duration)
        image_clip = image_clip.set_audio(AudioFileClip(audio_path))
        image_clip = image_clip.set_fps(24)
        image_clip = image_clip.set_duration(image_clip.audio.duration)

        image_clip.write_videofile(
            output_path, codec='libx264', audio_codec='aac')
        os.remove(temp_img_path)
        return output_path
    except Exception as e:
        return f"Error al crear video del tema: {str(e)}"


def generate_complete_video(topics: list, base_filename: str = "video_tema", send_percentage=None, work_directory: Optional[str] = None) -> str:
    """Genera un video completo combinando todos los temas."""
    try:
        print(f"🎬 Iniciando generación de video completo")
        print(f"📊 Total de temas a procesar: {len(topics)}")

        if send_percentage:
            send_percentage(0)

        # Usar directorio proporcionado o crear uno nuevo
        if not work_directory:
            work_directory = create_work_directory()

        total_steps = len(topics) * 2 + 1
        current_step = 0

        for i, topic in enumerate(topics):
            current_step += 1
            progress = int((current_step / total_steps) * 100)

            print(f"🖼️  Procesando imagen para tema {i+1}: {topic['titulo']}")
            if send_percentage:
                send_percentage(progress)

            if 'imagen_url' in topic and not topic['imagen_url'].startswith('Error'):
                image_filename = os.path.join(
                    work_directory, f"{base_filename}_imagen_{i+1}.png")
                local_image = download_image(
                    topic['imagen_url'], image_filename)
                if local_image:
                    topic['imagen_local'] = local_image
                    print(f"✅ Imagen descargada: {local_image}")
                else:
                    print(f"❌ Error al descargar imagen para tema {i+1}")
                    return f"Error: No se pudo descargar la imagen para el tema {i+1}"
            else:
                print(f"❌ No hay URL de imagen válida para tema {i+1}")
                return f"Error: No hay imagen disponible para el tema {i+1}"

        clips = []
        for i, topic in enumerate(topics):
            current_step += 1
            progress = int((current_step / total_steps) * 100)

            image_path = topic.get('imagen_local')
            audio_path = topic.get('archivo_audio')
            if not image_path or not audio_path:
                return f"Error: Faltan imagen o audio para el tema {i+1}"

            print(f"🎬 Creando video para tema {i+1}: {topic['titulo']}")
            if send_percentage:
                send_percentage(progress)

            output_path = os.path.join(
                work_directory, f"{base_filename}_{i+1}.mp4")
            clip_path = create_topic_video(
                image_path, audio_path, topic['titulo'], output_path)

            if clip_path.startswith("Error"):
                return clip_path

            clips.append(VideoFileClip(clip_path))
            print(f"✅ Video del tema {i+1} creado: {clip_path}")

        current_step += 1
        progress = int((current_step / total_steps) * 100)

        print(f"🎬 Combinando todos los videos...")
        if send_percentage:
            send_percentage(progress)

        final_video = concatenate_videoclips(clips, method="compose")
        video_output = os.path.join(
            work_directory, f"{base_filename}_completo.mp4")
        final_video.write_videofile(
            video_output, codec='libx264', audio_codec='aac')

        # Limpiar recursos
        for clip in clips:
            clip.close()

        print(f"✅ Video completo generado: {video_output}")
        if send_percentage:
            send_percentage(100)  # 100% - Completado

         
        return video_output

    except Exception as e:
        error_msg = f"Error al generar video completo: {str(e)}"
        print(error_msg)
        if send_percentage:
            send_percentage(-1)  # -1 indica error
        
        # En caso de error, no limpiar el directorio para preservar archivos para depuración
        return error_msg


def create_work_directory() -> str:
    """
    Crea un directorio de trabajo único con timestamp y UUID.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    directory = f"generados_{timestamp}_{unique_id}"

    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"📁 Directorio de trabajo creado: {directory}")

    return directory


def generate_audio_summary(title: str, topics: list, filename: str = "resumen_audio.mp3", work_directory: Optional[str] = None) -> str:
    """
    Genera un archivo de audio con el resumen completo de todos los temas.
    """
    try:
        print(f"🔊 Iniciando generación de audio resumen")
        print(f"📊 Total de temas a procesar: {len(topics)}")

        # Usar directorio proporcionado o crear uno nuevo
        if not work_directory:
            work_directory = create_work_directory()
        filename = os.path.join(work_directory, filename)

        # Crear texto completo para el audio
        full_text = f"{title}. "

        for i, topic in enumerate(topics):
            topic_title = topic.get('titulo', f'Tema {i+1}')
            topic_summary = topic.get('resumen', '')

            full_text += f"{topic_title}. {topic_summary}. "

            # Agregar puntos clave si existen
            if 'puntos_clave' in topic and topic['puntos_clave']:
                full_text += "Los puntos clave incluyen: "
                for j, punto in enumerate(topic['puntos_clave']):
                    if j == len(topic['puntos_clave']) - 1:
                        full_text += f"y {punto.lower()}. "
                    else:
                        full_text += f"{punto.lower()}, "

            # Agregar información adicional si existe
            if 'informacion_adicional' in topic and topic['informacion_adicional']:
                full_text += f"Además, es importante mencionar que {topic['informacion_adicional'].lower()}. "

        print(f"📝 Texto completo para audio: {len(full_text)} caracteres")
        print(f"📄 Muestra del texto: {full_text[:200]}...")

        # Generar audio con gTTS
        print(f"🎵 Generando audio: {filename}")
        tts = gTTS(text=full_text, lang='es', slow=False)
        tts.save(filename)

        file_size = os.path.getsize(filename)
        duration_estimate = len(full_text.split()) / \
            2.5  # Estimación aproximada
        print(
            f"✅ Audio generado: {filename} ({file_size} bytes, ~{duration_estimate:.1f}s)")
         
        return filename

    except Exception as e: 
        return f"Error al generar audio resumen: {str(e)}"


def generate_audio_by_topic(topics: list, base_filename: str = "tema", work_directory: Optional[str] = None) -> list:
    """
    Genera archivos de audio separados para cada tema.
    """
    try:
        print(f"🔊 Iniciando generación de audio por tema")
        print(f"📊 Total de temas a procesar: {len(topics)}")
        print(f"📁 Base filename: {base_filename}")

        # Usar directorio proporcionado o crear uno nuevo
        if not work_directory:
            work_directory = create_work_directory()

        audio_files = []

        for i, topic in enumerate(topics):
            print(
                f"🎯 Procesando tema {i+1}: {topic.get('titulo', f'Tema {i+1}')}")

            topic_title = topic.get('titulo', f'Tema {i+1}')
            topic_summary = topic.get('resumen', '')

            print(f"   📋 Título del tema: {topic_title}")
            print(f"   📖 Resumen del tema: {topic_summary[:100]}...")

            # Integrar puntos clave en el texto
            if 'puntos_clave' in topic and topic['puntos_clave']:
                print(
                    f"   🔑 Puntos clave encontrados: {len(topic['puntos_clave'])}")
                topic_summary += " Los puntos clave incluyen: "
                for j, punto in enumerate(topic['puntos_clave']):
                    if j == len(topic['puntos_clave']) - 1:
                        topic_summary += f"y {punto.lower()}. "
                    else:
                        topic_summary += f"{punto.lower()}, "
                print(f"   ✅ Puntos clave integrados")

            # Agregar información adicional si existe
            if 'informacion_adicional' in topic and topic['informacion_adicional']:
                topic_summary += f"Además, es importante mencionar que {topic['informacion_adicional'].lower()}. "
                print(
                    f"   📌 Información adicional: {topic['informacion_adicional'][:50]}...")
            else:
                print(f"   ⚠️  No hay información adicional")

            print(
                f"   📝 Texto final del tema: {len(topic_summary)} caracteres")
            print(f"   📄 Muestra del texto: {topic_summary[:100]}...")

            # Generar audio para este tema
            audio_filename = os.path.join(
                work_directory, f"{base_filename}_{i+1}.mp3")
            print(f"   🎵 Generando audio: {audio_filename}")

            try:
                tts = gTTS(text=topic_summary, lang='es', slow=False)
                tts.save(audio_filename)

                file_size = os.path.getsize(audio_filename)
                # Estimación aproximada
                duration_estimate = len(topic_summary.split()) / 2.5
                print(
                    f"   ✅ Audio generado: {audio_filename} ({file_size} bytes, ~{duration_estimate:.1f}s)")

                # Guardar la ruta del archivo de audio en el tema
                topic['archivo_audio'] = audio_filename

                audio_files.append({
                    'tema': topic_title,
                    'archivo_audio': audio_filename,
                    'tamaño': file_size,
                    'duración_estimada': f"{duration_estimate:.1f}s"
                })

            except Exception as e:
                error_msg = f"Error al generar audio para tema {i+1}: {str(e)}"
                print(f"   ❌ {error_msg}")
                audio_files.append({
                    'tema': topic_title,
                    'error': error_msg
                })

        print(
            f"🎉 Proceso completado. Total de archivos generados: {len(audio_files)}")
        
          
        return audio_files

    except Exception as e:
        
        return [{'error': f"Error al generar audios por tema: {str(e)}"}]


def generate_pdf_summary(title: str, topics: list, filename: str = "resumen.pdf", work_directory: Optional[str] = None) -> str:
    """
    Genera un PDF con la estructura: Título, tema, imagen, contenido para cada tema.
    """
    try:
        # Usar directorio proporcionado o crear uno nuevo
        if not work_directory:
            work_directory = create_work_directory()
        filename = os.path.join(work_directory, filename)

        doc = SimpleDocTemplate(filename, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()

        # Estilo personalizado para el título principal
        title_style = ParagraphStyle(
            'TituloPrincipal',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1,  # Centrado
            textColor=colors.darkblue
        )

        # Estilo para subtítulos de temas
        topic_style = ParagraphStyle(
            'TemaStyle',
            parent=styles['Heading2'],
            fontSize=18,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.darkgreen
        )

        # Estilo para el contenido de texto fluido
        content_style = ParagraphStyle(
            'ContenidoStyle',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=12,
            leading=16,  # Espaciado entre líneas
            alignment=0,  # Justificado
            textColor=colors.black
        )

        # Agregar título principal
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 20))

        # Procesar cada tema
        for i, topic in enumerate(topics):
            # Título del tema
            story.append(Paragraph(f"<b>{topic['titulo']}</b>", topic_style))

            # Imagen del tema (si existe y no es un error)
            if 'imagen_url' in topic and not topic['imagen_url'].startswith('Error'):
                try:
                    # Descargar imagen
                    response = requests.get(topic['imagen_url'])
                    if response.status_code == 200:
                        img_data = io.BytesIO(response.content)
                        img = Image(img_data, width=4*inch, height=4*inch)
                        img.hAlign = 'CENTER'
                        story.append(img)
                        story.append(Spacer(1, 10))
                except Exception as e:
                    story.append(
                        Paragraph(f"<i>Error al cargar imagen: {str(e)}</i>", styles['Normal']))

            # Contenido del tema como texto fluido
            content_text = topic['resumen']

            # Agregar puntos clave como parte del texto fluido
            if 'puntos_clave' in topic and topic['puntos_clave']:
                content_text += " Los puntos clave incluyen: "
                for j, punto in enumerate(topic['puntos_clave']):
                    if j == len(topic['puntos_clave']) - 1:
                        content_text += f"y {punto.lower()}. "
                    else:
                        content_text += f"{punto.lower()}, "

            # Agregar información adicional si existe
            if 'informacion_adicional' in topic and topic['informacion_adicional']:
                content_text += f" Además, es importante mencionar que {topic['informacion_adicional'].lower()}. "

            story.append(Paragraph(content_text, content_style))
            story.append(Spacer(1, 15))

            # Agregar salto de página si no es el último tema
            if i < len(topics) - 1:
                story.append(PageBreak())

        # Construir el PDF
        doc.build(story)
         
        return filename

    except Exception as e:
        return f"Error al generar PDF: {str(e)}"


def clean_working_directory(directory: str) -> None:
    """
    Elimina el directorio de trabajo y todos sus contenidos.
    """
    try:
        if os.path.exists(directory):
            shutil.rmtree(directory)
            print(f"🧹 Directorio de trabajo eliminado: {directory}")
        else:
            print(f"⚠️  Directorio no encontrado: {directory}")
    except Exception as e:
        print(f"❌ Error al eliminar directorio de trabajo: {str(e)}")
