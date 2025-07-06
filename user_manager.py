import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class UserInfo:
    """Información básica del usuario"""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = None
    is_bot: bool = False
    first_seen: str = None
    last_activity: str = None
    total_files_processed: int = 0
    total_generations: int = 0
    preferred_language: str = "es"


@dataclass
class UserSession:
    """Sesión actual del usuario"""
    user_id: int
    current_file: Optional[str] = None
    current_file_size: Optional[int] = None
    extracted_text: Optional[str] = None
    organized_topics: Optional[dict] = None
    session_start: str = None
    last_action: str = None


@dataclass
class UserActivity:
    """Actividad del usuario"""
    user_id: int
    action: str
    timestamp: str
    details: Optional[dict] = None
    file_processed: Optional[str] = None
    generation_type: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None


class UserManager:
    """Gestor de usuarios para el bot"""

    def __init__(self, data_dir: str = "user_data"):
        self.data_dir = data_dir
        self.users_file = os.path.join(data_dir, "users.json")
        self.sessions_file = os.path.join(data_dir, "sessions.json")
        self.activities_file = os.path.join(data_dir, "activities.json")

        os.makedirs(data_dir, exist_ok=True)

        self.users: Dict[int, UserInfo] = self._load_users()
        self.sessions: Dict[int, UserSession] = self._load_sessions()
        self.activities: List[UserActivity] = self._load_activities()

    def _load_users(self) -> Dict[int, UserInfo]:
        """Carga usuarios desde archivo JSON"""
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {
                        int(user_id): UserInfo(**user_data)
                        for user_id, user_data in data.items()
                    }
        except Exception as e:
            logger.error(f"Error cargando usuarios: {e}")
        return {}

    def _save_users(self):
        """Guarda usuarios en archivo JSON"""
        try:
            data = {
                str(user_id): asdict(user_info)
                for user_id, user_info in self.users.items()
            }
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error guardando usuarios: {e}")

    def _load_sessions(self) -> Dict[int, UserSession]:
        """Carga sesiones desde archivo JSON"""
        try:
            if os.path.exists(self.sessions_file):
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {
                        int(user_id): UserSession(**session_data)
                        for user_id, session_data in data.items()
                    }
        except Exception as e:
            logger.error(f"Error cargando sesiones: {e}")
        return {}

    def _save_sessions(self):
        """Guarda sesiones en archivo JSON"""
        try:
            data = {
                str(user_id): asdict(session)
                for user_id, session in self.sessions.items()
            }
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error guardando sesiones: {e}")

    def _load_activities(self) -> List[UserActivity]:
        """Carga actividades desde archivo JSON"""
        try:
            if os.path.exists(self.activities_file):
                with open(self.activities_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return [UserActivity(**activity_data) for activity_data in data]
        except Exception as e:
            logger.error(f"Error cargando actividades: {e}")
        return []

    def _save_activities(self):
        """Guarda actividades en archivo JSON"""
        try:
            data = [asdict(activity) for activity in self.activities]
            with open(self.activities_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error guardando actividades: {e}")

    def register_user(self, user_id: int, username: str = None, first_name: str = None,
                      last_name: str = None, language_code: str = None, is_bot: bool = False) -> UserInfo:
        """Registra un nuevo usuario o actualiza información existente"""
        now = datetime.now().isoformat()

        if user_id in self.users:
            user = self.users[user_id]
            user.username = username or user.username
            user.first_name = first_name or user.first_name
            user.last_name = last_name or user.last_name
            user.language_code = language_code or user.language_code
            user.is_bot = is_bot
            user.last_activity = now
        else:
            user = UserInfo(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code,
                is_bot=is_bot,
                first_seen=now,
                last_activity=now
            )
            self.users[user_id] = user

        self._save_users()
        return user

    def get_user(self, user_id: int) -> Optional[UserInfo]:
        """Obtiene información de un usuario"""
        return self.users.get(user_id)

    def update_user_activity(self, user_id: int):
        """Actualiza la última actividad del usuario"""
        if user_id in self.users:
            self.users[user_id].last_activity = datetime.now().isoformat()
            self._save_users()

    def start_session(self, user_id: int, filename: str = None, file_size: int = None) -> UserSession:
        """Inicia una nueva sesión para el usuario"""
        now = datetime.now().isoformat()

        session = UserSession(
            user_id=user_id,
            current_file=filename,
            current_file_size=file_size,
            session_start=now,
            last_action=now
        )

        self.sessions[user_id] = session
        self._save_sessions()
        return session

    def get_session(self, user_id: int) -> Optional[UserSession]:
        """Obtiene la sesión actual del usuario"""
        return self.sessions.get(user_id)

    def update_session(self, user_id: int, **kwargs):
        """Actualiza la sesión del usuario"""
        if user_id in self.sessions:
            session = self.sessions[user_id]
            for key, value in kwargs.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            session.last_action = datetime.now().isoformat()
            self._save_sessions()

    def end_session(self, user_id: int):
        """Termina la sesión del usuario"""
        if user_id in self.sessions:
            del self.sessions[user_id]
            self._save_sessions()

    def log_activity(self, user_id: int, action: str, success: bool = True,
                     details: dict = None, file_processed: str = None,
                     generation_type: str = None, error_message: str = None):
        """Registra una actividad del usuario"""
        activity = UserActivity(
            user_id=user_id,
            action=action,
            timestamp=datetime.now().isoformat(),
            details=details,
            file_processed=file_processed,
            generation_type=generation_type,
            success=success,
            error_message=error_message
        )

        self.activities.append(activity)

        if user_id in self.users:
            user = self.users[user_id]
            if action == "file_uploaded":
                user.total_files_processed += 1
            elif action in ["pdf_generated", "audio_generated", "video_generated"]:
                user.total_generations += 1

        self._save_activities()
        self._save_users()

    def get_user_stats(self, user_id: int) -> dict:
        """Obtiene estadísticas del usuario"""
        user = self.get_user(user_id)
        if not user:
            return {}

        user_activities = [a for a in self.activities if a.user_id == user_id]
        activity_counts = {}
        for activity in user_activities:
            activity_counts[activity.action] = activity_counts.get(
                activity.action, 0) + 1

        return {
            "user_info": asdict(user),
            "total_activities": len(user_activities),
            "activity_breakdown": activity_counts,
            "success_rate": len([a for a in user_activities if a.success]) / len(user_activities) if user_activities else 0
        }

    def get_all_users_stats(self) -> dict:
        """Obtiene estadísticas de todos los usuarios"""
        total_users = len(self.users)
        total_activities = len(self.activities)
        total_files = sum(
            user.total_files_processed for user in self.users.values())
        total_generations = sum(
            user.total_generations for user in self.users.values())

        now = datetime.now()
        active_users = 0
        for user in self.users.values():
            if user.last_activity:
                last_activity = datetime.fromisoformat(user.last_activity)
                if (now - last_activity).days < 1:
                    active_users += 1

        return {
            "total_users": total_users,
            "active_users_24h": active_users,
            "total_activities": total_activities,
            "total_files_processed": total_files,
            "total_generations": total_generations
        }

    def export_user_data(self, user_id: int) -> dict:
        """Exporta todos los datos de un usuario"""
        user = self.get_user(user_id)
        session = self.get_session(user_id)
        user_activities = [a for a in self.activities if a.user_id == user_id]

        return {
            "user_info": asdict(user) if user else None,
            "current_session": asdict(session) if session else None,
            "activities": [asdict(activity) for activity in user_activities],
            "stats": self.get_user_stats(user_id)
        }
