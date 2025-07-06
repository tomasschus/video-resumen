import os
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import openai
from utils import extract_pdf_text, generate_pdf_summary, generate_audio_summary, generate_audio_by_topic, generate_complete_video
from utils_ai import generate_image_with_openai, divide_into_topics
from typing import List

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

if not openai.api_key:
    print("ADVERTENCIA: OPENAI_API_KEY no está configurada en el archivo .env")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "OK"}


@app.post("/upload-pdf/")
async def upload_pdf(files: List[UploadFile] = File(...)):
    results = []
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            results.append({"filename": file.filename,
                            "error": "El archivo debe ser un PDF."})
            continue
        try:
            content = await file.read()
            extracted_text = extract_pdf_text(content)
            organized_topics = await divide_into_topics(extracted_text)
            results.append({
                "filename": file.filename,
                "size": len(content),
                "text": extracted_text,
                "topics": organized_topics
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "error": f"Error procesando el archivo: {str(e)}"
            })
    return results


@app.post("/generate-pdf-resumen/")
async def generate_pdf_summary_endpoint(files: List[UploadFile] = File(...)):
    """Genera un PDF con la estructura: Título, tema, imagen, contenido para cada tema."""
    try:
        if not files:
            return JSONResponse(status_code=400, content={"error": "No se proporcionaron archivos"})

        file = files[0]
        print(f"Procesando archivo: {file.filename}")

        if not file.filename.lower().endswith('.pdf'):
            return JSONResponse(status_code=400, content={"error": "El archivo debe ser un PDF"})

        content = await file.read()
        print(f"Archivo leído, tamaño: {len(content)} bytes")

        extracted_text = extract_pdf_text(content)
        print(f"Texto extraído, longitud: {len(extracted_text)} caracteres")

        organized_topics = await divide_into_topics(extracted_text)
        print(
            f"Temas organizados: {len(organized_topics.get('temas', []))} temas")

        if "error" in organized_topics:
            return JSONResponse(status_code=500, content={"error": organized_topics["error"]})

        title = f"Resumen de {file.filename}"
        filename = f"resumen_{file.filename.replace('.pdf', '')}.pdf"
        print(f"Generando PDF: {filename}")

        pdf_path = generate_pdf_summary(
            title, organized_topics["temas"], filename)
        print(f"PDF generado en: {pdf_path}")

        if pdf_path.startswith("Error"):
            return JSONResponse(status_code=500, content={"error": pdf_path})

        if not os.path.exists(pdf_path):
            return JSONResponse(status_code=500, content={"error": f"El archivo PDF no se generó correctamente: {pdf_path}"})

        return FileResponse(
            path=pdf_path,
            filename=filename,
            media_type="application/pdf"
        )

    except Exception as e:
        print(f"Error en generate_pdf_summary_endpoint: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/generate-audio-resumen/")
async def generate_audio_summary_endpoint(files: List[UploadFile] = File(...)):
    """Genera un archivo de audio leyendo el resumen completo."""
    try:
        print(f"🎵 Endpoint /generate-audio-resumen/ llamado")

        if not files:
            print(f"❌ Error: No se proporcionaron archivos")
            return JSONResponse(status_code=400, content={"error": "No se proporcionaron archivos"})

        file = files[0]
        print(f"📁 Archivo recibido: {file.filename}")

        if not file.filename.lower().endswith('.pdf'):
            print(f"❌ Error: El archivo no es un PDF")
            return JSONResponse(status_code=400, content={"error": "El archivo debe ser un PDF"})

        print(f"📖 Leyendo contenido del archivo...")
        content = await file.read()
        print(f"📊 Tamaño del archivo: {len(content)} bytes")

        print(f"🔍 Extrayendo texto del PDF...")
        extracted_text = extract_pdf_text(content)
        print(f"📝 Texto extraído: {len(extracted_text)} caracteres")
        print(f"📄 Muestra del texto: {extracted_text[:200]}...")

        print(f"🤖 Procesando con ChatGPT para dividir en temas...")
        organized_topics = await divide_into_topics(extracted_text)
        print(
            f"📋 Temas organizados: {len(organized_topics.get('temas', []))} temas")

        if "error" in organized_topics:
            print(
                f"❌ Error en la organización de temas: {organized_topics['error']}")
            return JSONResponse(status_code=500, content={"error": organized_topics["error"]})

        title = f"Resumen de {file.filename}"
        audio_filename = f"audio_resumen_{file.filename.replace('.pdf', '')}.mp3"
        print(f"🎵 Generando audio: {audio_filename}")

        audio_path = generate_audio_summary(
            title, organized_topics["temas"], audio_filename)
        print(f"📁 Ruta del audio generado: {audio_path}")

        if audio_path.startswith("Error"):
            print(f"❌ Error al generar audio: {audio_path}")
            return JSONResponse(status_code=500, content={"error": audio_path})

        if not os.path.exists(audio_path):
            print(f"❌ Error: El archivo de audio no existe en {audio_path}")
            return JSONResponse(status_code=500, content={"error": f"El archivo de audio no se generó correctamente: {audio_path}"})

        file_size = os.path.getsize(audio_path)
        print(
            f"✅ Audio generado exitosamente: {audio_path} ({file_size} bytes)")

        print(f"📤 Enviando archivo de audio al cliente...")
        return FileResponse(
            path=audio_path,
            filename=audio_filename,
            media_type="audio/mpeg"
        )

    except Exception as e:
        print(f"❌ Error en generate_audio_summary_endpoint: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/generate-audio-por-tema/")
async def generate_audio_by_topic_endpoint(files: List[UploadFile] = File(...)):
    """Genera archivos de audio separados para cada tema."""
    try:
        print(f"🎵 Endpoint /generate-audio-por-tema/ llamado")

        if not files:
            print(f"❌ Error: No se proporcionaron archivos")
            return JSONResponse(status_code=400, content={"error": "No se proporcionaron archivos"})

        file = files[0]
        print(f"📁 Archivo recibido: {file.filename}")

        if not file.filename.lower().endswith('.pdf'):
            print(f"❌ Error: El archivo no es un PDF")
            return JSONResponse(status_code=400, content={"error": "El archivo debe ser un PDF"})

        print(f"📖 Leyendo contenido del archivo...")
        content = await file.read()
        print(f"📊 Tamaño del archivo: {len(content)} bytes")

        print(f"🔍 Extrayendo texto del PDF...")
        extracted_text = extract_pdf_text(content)
        print(f"📝 Texto extraído: {len(extracted_text)} caracteres")

        print(f"🤖 Procesando con ChatGPT para dividir en temas...")
        organized_topics = await divide_into_topics(extracted_text)
        print(
            f"📋 Temas organizados: {len(organized_topics.get('temas', []))} temas")

        if "error" in organized_topics:
            print(
                f"❌ Error en la organización de temas: {organized_topics['error']}")
            return JSONResponse(status_code=500, content={"error": organized_topics["error"]})

        # Generar audios por tema
        base_filename = f"audio_tema_{file.filename.replace('.pdf', '')}"
        print(f"🎵 Generando audios por tema con base: {base_filename}")

        audio_files = generate_audio_by_topic(
            organized_topics["temas"], base_filename)
        print(f"📁 Archivos de audio generados: {len(audio_files)}")

        if "error" in audio_files[0]:
            print(
                f"❌ Error al generar audios por tema: {audio_files[0]['error']}")
            return JSONResponse(status_code=500, content={"error": audio_files[0]["error"]})

        successful_files = len(
            [a for a in audio_files if 'archivo_audio' in a])
        print(
            f"✅ Proceso completado: {successful_files}/{len(audio_files)} archivos generados exitosamente")

        return {
            "mensaje": "Audios generados exitosamente",
            "archivos_audio": audio_files,
            "total_temas": len(audio_files),
            "archivos_exitosos": successful_files
        }

    except Exception as e:
        print(f"❌ Error en generate_audio_by_topic_endpoint: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/generate-video-completo/")
async def generate_complete_video_endpoint(files: List[UploadFile] = File(...)):
    """
    Genera un video completo combinando imágenes y audios de todos los temas.
    """
    try:
        print(f"🎬 Endpoint /generate-video-completo/ llamado")

        if not files:
            print(f"❌ Error: No se proporcionaron archivos")
            return JSONResponse(status_code=400, content={"error": "No se proporcionaron archivos"})

        file = files[0]
        print(f"📁 Archivo recibido: {file.filename}")

        if not file.filename.lower().endswith('.pdf'):
            print(f"❌ Error: El archivo no es un PDF")
            return JSONResponse(status_code=400, content={"error": "El archivo debe ser un PDF"})

        print(f"📖 Leyendo contenido del archivo...")
        content = await file.read()
        print(f"📊 Tamaño del archivo: {len(content)} bytes")

        print(f"🔍 Extrayendo texto del PDF...")
        extracted_text = extract_pdf_text(content)
        print(f"📝 Texto extraído: {len(extracted_text)} caracteres")

        print(f"🤖 Procesando con ChatGPT para dividir en temas...")
        organized_topics = await divide_into_topics(extracted_text)
        print(
            f"📋 Temas organizados: {len(organized_topics.get('temas', []))} temas")

        if "error" in organized_topics:
            print(
                f"❌ Error en la organización de temas: {organized_topics['error']}")
            return JSONResponse(status_code=500, content={"error": organized_topics["error"]})

        # Generar audios por tema primero
        base_filename = f"video_tema_{file.filename.replace('.pdf', '')}"
        print(f"🎵 Generando audios por tema para video...")

        audio_files = generate_audio_by_topic(
            organized_topics["temas"], base_filename)
        print(f"📁 Archivos de audio generados: {len(audio_files)}")

        if "error" in audio_files[0]:
            print(
                f"❌ Error al generar audios por tema: {audio_files[0]['error']}")
            return JSONResponse(status_code=500, content={"error": audio_files[0]["error"]})

        # Generar video completo
        print(f"🎬 Generando video completo...")
        video_path = generate_complete_video(
            organized_topics["temas"], base_filename)
        print(f"📁 Ruta del video generado: {video_path}")

        if video_path.startswith("Error"):
            print(f"❌ Error al generar video: {video_path}")
            return JSONResponse(status_code=500, content={"error": video_path})

        # Verificar que el archivo existe
        if not os.path.exists(video_path):
            print(f"❌ Error: El archivo de video no existe en {video_path}")
            return JSONResponse(status_code=500, content={"error": f"El archivo de video no se generó correctamente: {video_path}"})

        file_size = os.path.getsize(video_path)
        print(
            f"✅ Video generado exitosamente: {video_path} ({file_size} bytes)")

        # Devolver el archivo de video
        print(f"📤 Enviando archivo de video al cliente...")
        return FileResponse(
            path=video_path,
            filename=video_path,
            media_type="video/mp4"
        )

    except Exception as e:
        print(f"❌ Error en generate_complete_video_endpoint: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/generate-image/")
async def generate_image(prompt: str = Form(...)):
    try:
        image_url = generate_image_with_openai(prompt)
        return {"image_url": image_url}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
