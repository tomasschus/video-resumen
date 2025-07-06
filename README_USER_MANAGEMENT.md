# Sistema de Gestión de Usuarios del Bot

## 📋 Descripción

El bot ahora incluye un sistema completo de gestión de usuarios que permite:

- **Registrar usuarios** automáticamente cuando interactúan con el bot
- **Rastrear actividades** de cada usuario (subida de archivos, generaciones, errores)
- **Mantener sesiones** activas durante el procesamiento
- **Generar estadísticas** detalladas de uso
- **Exportar datos** de usuarios para análisis

## 🏗️ Arquitectura

### Archivos Principales

- `user_manager.py` - Clase principal para gestión de usuarios
- `bot.py` - Bot integrado con el sistema de usuarios
- `bot_stats.py` - Script para administración y estadísticas
- `test_user_manager.py` - Script de pruebas del sistema

### Estructura de Datos

#### UserInfo

```python
@dataclass
class UserInfo:
    user_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    language_code: Optional[str]
    is_bot: bool
    first_seen: str
    last_activity: str
    total_files_processed: int
    total_generations: int
    preferred_language: str
```

#### UserSession

```python
@dataclass
class UserSession:
    user_id: int
    current_file: Optional[str]
    current_file_size: Optional[int]
    extracted_text: Optional[str]
    organized_topics: Optional[dict]
    session_start: str
    last_action: str
```

#### UserActivity

```python
@dataclass
class UserActivity:
    user_id: int
    action: str
    timestamp: str
    details: Optional[dict]
    file_processed: Optional[str]
    generation_type: Optional[str]
    success: bool
    error_message: Optional[str]
```

## 📁 Almacenamiento de Datos

Los datos se guardan en archivos JSON en el directorio `user_data/`:

- `users.json` - Información de usuarios registrados
- `sessions.json` - Sesiones activas de usuarios
- `activities.json` - Historial de actividades

### Ejemplo de Estructura de Datos

```json
{
  "123456789": {
    "user_id": 123456789,
    "username": "usuario_ejemplo",
    "first_name": "Juan",
    "last_name": "Pérez",
    "language_code": "es",
    "is_bot": false,
    "first_seen": "2024-01-15T10:30:00",
    "last_activity": "2024-01-15T14:45:00",
    "total_files_processed": 5,
    "total_generations": 8,
    "preferred_language": "es"
  }
}
```

## 🚀 Funcionalidades

### 1. Registro Automático de Usuarios

Los usuarios se registran automáticamente cuando:

- Ejecutan `/start`
- Suben un archivo PDF
- Interactúan con cualquier comando

### 2. Seguimiento de Actividades

Se registran automáticamente las siguientes actividades:

| Actividad                | Descripción            | Éxito |
| ------------------------ | ---------------------- | ----- |
| `bot_started`            | Usuario inicia el bot  | ✅    |
| `file_uploaded`          | Subida exitosa de PDF  | ✅    |
| `pdf_generated`          | Generación de PDF      | ✅    |
| `audio_generated`        | Generación de audio    | ✅    |
| `video_generated`        | Generación de video    | ✅    |
| `invalid_file_uploaded`  | Archivo no válido      | ❌    |
| `file_too_large`         | Archivo muy grande     | ❌    |
| `text_extraction_failed` | Error extracción texto | ❌    |
| `generation_failed`      | Error en generación    | ❌    |

### 3. Comandos de Usuario

#### `/stats` - Ver Estadísticas Personales

```
📊 Tus Estadísticas

👤 Usuario: Juan Pérez
🆔 ID: 123456789
📅 Primera vez: 2024-01-15
🕐 Última actividad: 2024-01-15

📈 Actividad Total:
• 📁 Archivos procesados: 5
• 🎯 Generaciones completadas: 8
• 📊 Total de actividades: 15
• ✅ Tasa de éxito: 93.3%
```

### 4. Panel de Administración

Ejecuta `python bot_stats.py` para acceder al panel de administración:

```
🤖 Panel de Administración del Bot
==================================================
1. 📊 Mostrar estadísticas generales
2. 👤 Mostrar detalles de usuario
3. 📋 Mostrar resumen de actividades
4. 📄 Exportar datos de usuario específico
5. 📁 Exportar datos de todos los usuarios
6. 🚪 Salir
```

## 🧪 Pruebas

### Ejecutar Pruebas del Sistema

```bash
python test_user_manager.py
```

### Verificar Funcionamiento

```bash
python bot_stats.py
```

## 📊 Estadísticas Disponibles

### Por Usuario

- Información personal
- Historial de actividades
- Archivos procesados
- Generaciones completadas
- Tasa de éxito
- Última actividad

### Globales

- Total de usuarios registrados
- Usuarios activos (24h)
- Total de actividades
- Archivos procesados
- Generaciones completadas
- Tasa de éxito general

## 🔧 Configuración

### Variables de Entorno

No se requieren variables adicionales. El sistema funciona con la configuración existente del bot.

### Directorio de Datos

Por defecto, los datos se guardan en `user_data/`. Puedes cambiar esto al inicializar el UserManager:

```python
user_manager = UserManager("mi_directorio_personalizado")
```

## 📈 Análisis de Datos

### Exportar Datos de Usuario

```python
from user_manager import UserManager

manager = UserManager()
user_data = manager.export_user_data(123456789)
```

### Exportar Todos los Datos

```python
all_users_data = {}
for user_id in manager.users.keys():
    all_users_data[user_id] = manager.export_user_data(user_id)
```

## 🔒 Privacidad y Seguridad

### Datos Almacenados

- ID de usuario de Telegram
- Nombre y username (si están disponibles)
- Historial de actividades
- Estadísticas de uso

### Datos NO Almacenados

- Contenido de archivos PDF
- Texto extraído de documentos
- Archivos generados
- Información personal sensible

### Cumplimiento GDPR

- Los usuarios pueden solicitar sus datos con `/stats`
- Los datos se almacenan localmente
- No se comparten con terceros

## 🚀 Mejoras Futuras

### Funcionalidades Planificadas

- [ ] Dashboard web para administración
- [ ] Notificaciones automáticas
- [ ] Sistema de límites por usuario
- [ ] Análisis de uso avanzado
- [ ] Backup automático de datos
- [ ] Integración con base de datos

### Métricas Adicionales

- [ ] Tiempo promedio de procesamiento
- [ ] Tipos de archivos más populares
- [ ] Horarios de mayor actividad
- [ ] Patrones de uso por región

## 📞 Soporte

Para problemas o preguntas sobre el sistema de gestión de usuarios:

1. Revisa los logs del bot
2. Ejecuta las pruebas con `test_user_manager.py`
3. Verifica la integridad de los archivos JSON
4. Consulta este documento

---

**Nota**: Este sistema está diseñado para ser escalable y mantener la privacidad de los usuarios mientras proporciona información valiosa para mejorar el servicio.
