import openai
import json
import asyncio
import aiohttp
import os
from datetime import datetime
import uuid


def create_work_directory() -> str:
    """Crea un directorio de trabajo único con timestamp y UUID."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    directory = f"generados_{timestamp}_{unique_id}"

    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"📁 Directorio de trabajo creado: {directory}")

    return directory


def generate_image_with_openai(prompt: str) -> str:
    """Genera una imagen usando la API de OpenAI a partir de un prompt y devuelve la URL de la imagen."""
    response = openai.images.generate(
        model="dall-e-3",
        prompt=prompt,
        n=1,
        size="1024x1024"
    )
    return response.data[0].url


async def generate_image_async(session, prompt: str) -> str:
    """Genera una imagen de forma asíncrona usando la API de OpenAI."""
    try:
        response = openai.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024"
        )
        return response.data[0].url
    except Exception as e:
        return f"Error al generar imagen: {str(e)}"


async def divide_into_topics(text: str) -> dict:
    """Usa ChatGPT para dividir el texto en temas organizados y devuelve un objeto JSON."""

    try:
        try:
            with open('divide_into_topic.prompt.txt', 'r', encoding='utf-8') as file:
                prompt_template = file.read()
        except FileNotFoundError:
            return {
                "error": "No se encontró el archivo divide_into_topic.prompt.txt"
            }
        except Exception as e:
            return {
                "error": f"Error al leer el archivo de prompt: {str(e)}"
            }

        work_directory = create_work_directory()

        prompt = prompt_template.replace("{{text_to_analize}}", text)

        with open(os.path.join(work_directory, 'prompt.txt'), 'w', encoding='utf-8') as f:
            f.write(prompt)

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un experto en análisis y organización de contenido técnico y académico, especializado en crear resúmenes narrativos, fluidos y REFINADOS. Tu tarea es dividir textos en temas claros y estructurados, enfocándote ÚNICAMENTE en el contenido técnico, académico o temático del documento. Es FUNDAMENTAL que NO pierdas ninguna información del texto original y que NO hagas referencias innecesarias a instituciones educativas. Debes preservar todos los detalles, fechas, nombres y datos específicos del contenido principal. Los resúmenes deben ser naturales, fluidos, CONCISOS y optimizados para ser leídos en voz alta, eliminando redundancias y repeticiones innecesarias. Enfócate en explicar los conceptos directamente, no en mencionar dónde se enseñan. Responde ÚNICAMENTE con JSON válido, sin markdown."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000
        )

        response_text = response.choices[0].message.content.strip()

        if response_text.startswith("```json"):
            response_text = response_text.replace(
                "```json", "").replace("```", "").strip()
        elif response_text.startswith("```"):
            response_text = response_text.replace("```", "").strip()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        response_filename = os.path.join(
            work_directory, f"response_ai_{timestamp}.txt")

        with open(response_filename, 'w', encoding='utf-8') as f:
            f.write(response_text)

        topics_json = json.loads(response_text)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        topics_filename = os.path.join(
            work_directory, f"temas_generados_{timestamp}.json")

        try:
            with open(topics_filename, 'w', encoding='utf-8') as f:
                json.dump(topics_json, f, ensure_ascii=False, indent=2)
            print(f"💾 Temas guardados en: {topics_filename}")

            topics_json["archivo_temas"] = topics_filename

        except Exception as e:
            print(f"⚠️  Error al guardar archivo de temas: {str(e)}")

        async with aiohttp.ClientSession() as session:
            tasks = []
            for topic in topics_json.get("temas", []):
                image_prompt = f"Crear una imagen representativa para el contenido técnico: {topic['titulo']}. {topic['resumen'][:200]}... Enfócate en el concepto técnico, no en la institución educativa."
                task = generate_image_async(session, image_prompt)
                tasks.append(task)

            image_urls = await asyncio.gather(*tasks, return_exceptions=True)

            for i, topic in enumerate(topics_json.get("temas", [])):
                if isinstance(image_urls[i], Exception):
                    topic["imagen_url"] = f"Error al generar imagen: {str(image_urls[i])}"
                else:
                    topic["imagen_url"] = image_urls[i]

        return topics_json

    except json.JSONDecodeError as e:
        return {
            "error": f"Error al parsear JSON de ChatGPT: {str(e)}",
            "respuesta_raw": response.choices[0].message.content if 'response' in locals() else "No hay respuesta"
        }
    except Exception as e:
        return {
            "error": f"Error al procesar con ChatGPT: {str(e)}"
        }
