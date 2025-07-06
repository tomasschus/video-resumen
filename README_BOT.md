# 🤖 Bot de Telegram para Resumen de PDFs

Este bot de Telegram ofrece la misma funcionalidad que la API de FastAPI, pero a través de la interfaz de Telegram.

## 🚀 Configuración

### 1. Crear un Bot de Telegram

1. Ve a [@BotFather](https://t.me/botfather) en Telegram
2. Envía `/newbot`
3. Sigue las instrucciones para crear tu bot
4. Guarda el token que te proporciona

### 2. Configurar Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto con:

```env
# OpenAI API Key
OPENAI_API_KEY=tu_openai_api_key_aqui

# Telegram Bot Token
TELEGRAM_BOT_TOKEN=tu_telegram_bot_token_aqui
```

### 3. Instalar Dependencias

```bash
pip install python-telegram-bot
```

## 🎯 Funcionalidades

El bot puede:

- **📄 Generar PDFs resumen** con temas, imágenes y contenido organizado
- **🎵 Crear audios del resumen completo** en español
- **🎵 Generar audios por tema** separados
- **🎬 Crear videos completos** combinando imágenes y audios

## 📱 Cómo Usar

### Comandos Disponibles

- `/start` - Mensaje de bienvenida
- `/help` - Mostrar ayuda
- `/status` - Ver estado del procesamiento

### Flujo de Uso

1. **Enviar PDF**: Envía un archivo PDF al bot (máximo 20MB)
2. **Procesamiento**: El bot extraerá el texto y lo dividirá en temas
3. **Seleccionar opción**: Elige qué tipo de resumen quieres generar
4. **Recibir archivo**: Espera a que se procese y recibe tu archivo

### Ejemplo de Uso

```
Usuario: /start
Bot: 🤖 Bienvenido al Bot de Resumen de PDFs...

Usuario: [envía archivo PDF]
Bot: ✅ PDF procesado exitosamente!
     📝 Texto extraído: 5000 caracteres
     📋 Temas encontrados: 4

     ¿Qué tipo de resumen quieres generar?
     [📄 PDF Resumen] [🎵 Audio Resumen]
     [🎵 Audio por Tema] [🎬 Video Completo]

Usuario: [selecciona opción]
Bot: ✅ Archivo enviado exitosamente!
```

## 🔧 Ejecutar el Bot

```bash
python bot.py
```

## 📋 Características Técnicas

- **Límite de archivo**: 20MB máximo
- **Idioma de audio**: Español
- **Formato de video**: MP4
- **Formato de audio**: MP3
- **Formato de PDF**: A4 con estilos personalizados

## 🛠️ Estructura del Código

- `bot.py` - Lógica principal del bot
- `utils.py` - Funciones de procesamiento (sin IA)
- `utils_ai.py` - Funciones que usan GPT/OpenAI
- `main.py` - API de FastAPI (alternativa)

## 🔒 Seguridad

- Los archivos se procesan temporalmente
- No se almacenan permanentemente
- Cada usuario tiene su propio estado de procesamiento
- Validación de tipos de archivo y tamaños

## 🚨 Notas Importantes

- El procesamiento puede tomar varios minutos
- Los archivos se procesan uno por uno
- El bot mantiene el contenido técnico, no referencias institucionales
- Los videos incluyen imágenes generadas por IA
