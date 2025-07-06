# API de carga de PDFs

## Requisitos

- Python 3.8+
- (Opcional) Crear y activar un entorno virtual:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```
- Instalar dependencias:
  ```bash
  pip install -r requirements.txt
  ```

## Uso

1. Ejecutar el servidor:
   ```bash
   uvicorn main:app --reload
   ```
2. Ir a [http://localhost:8000/docs](http://localhost:8000/docs) para probar el endpoint `/upload-pdf/` y subir archivos PDF.

## Endpoint

- `POST /upload-pdf/`
  - Recibe: archivo PDF (form-data, campo `file`)
  - Responde: nombre y tamaño del archivo
