#!/usr/bin/env python3
"""
Script para mostrar estadísticas del bot y exportar datos de usuarios.
"""

import json
from datetime import datetime
from typing import Optional

from user_manager import UserManager


def show_bot_stats():
    """Muestra estadísticas generales del bot."""
    print("🤖 **Estadísticas del Bot de Resumen de PDFs**")
    print("=" * 50)

    manager = UserManager()
    stats = manager.get_all_users_stats()

    print(f"\n📊 **Estadísticas Generales:**")
    print(f"👥 Total de usuarios: {stats['total_users']}")
    print(f"🟢 Usuarios activos (24h): {stats['active_users_24h']}")
    print(f"📈 Total de actividades: {stats['total_activities']}")
    print(f"📁 Archivos procesados: {stats['total_files_processed']}")
    print(f"🎯 Generaciones completadas: {stats['total_generations']}")

    if stats['total_files_processed'] > 0:
        success_rate = (stats['total_generations'] /
                        stats['total_files_processed']) * 100
        print(f"✅ Tasa de éxito: {success_rate:.1f}%")

    print(f"\n🏆 **Usuarios Más Activos:**")
    users = list(manager.users.values())
    
    # Calcular total_activities para cada usuario
    user_activities = {}
    for activity in manager.activities:
        user_id = activity.user_id
        user_activities[user_id] = user_activities.get(user_id, 0) + 1
    
    # Ordenar usuarios por número de actividades
    users.sort(key=lambda x: user_activities.get(x.user_id, 0), reverse=True)

    for i, user in enumerate(users[:5], 1):
        user_activity_count = user_activities.get(user.user_id, 0)
        print(f"{i}. {user.first_name or 'Usuario'} {user.last_name or ''} "
              f"(@{user.username or 'sin_username'})")
        print(f"   📁 Archivos: {user.total_files_processed} | "
              f"🎯 Generaciones: {user.total_generations} | "
              f"📈 Actividades: {user_activity_count} | "
              f"📅 Última actividad: {user.last_activity[:10] if user.last_activity else 'N/A'}")


def export_user_data(user_id: Optional[int] = None):
    """Exporta datos de un usuario específico o todos los usuarios."""
    manager = UserManager()

    if user_id:
        user_data = manager.export_user_data(user_id)
        filename = f"user_data_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)

        print(f"✅ Datos del usuario {user_id} exportados a: {filename}")

    else:
        all_users_data = {}
        for user_id in manager.users.keys():
            all_users_data[user_id] = manager.export_user_data(user_id)

        filename = f"all_users_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_users_data, f, ensure_ascii=False, indent=2)

        print(f"✅ Datos de todos los usuarios exportados a: {filename}")


def show_user_details(user_id: int):
    """Muestra detalles específicos de un usuario."""
    manager = UserManager()
    user_data = manager.export_user_data(user_id)

    if not user_data['user_info']:
        print(f"❌ Usuario {user_id} no encontrado.")
        return

    user_info = user_data['user_info']
    activities = user_data['activities']

    print(f"\n👤 **Detalles del Usuario {user_id}:**")
    print(f"Nombre: {user_info['first_name']} {user_info['last_name']}")
    print(f"Username: @{user_info['username']}")
    print(f"Idioma: {user_info['language_code']}")
    print(f"Primera vez: {user_info['first_seen']}")
    print(f"Última actividad: {user_info['last_activity']}")
    print(f"Archivos procesados: {user_info['total_files_processed']}")
    print(f"Generaciones: {user_info['total_generations']}")

    print(f"\n📋 **Últimas 10 Actividades:**")
    recent_activities = sorted(
        activities, key=lambda x: x['timestamp'], reverse=True)[:10]

    for activity in recent_activities:
        timestamp = activity['timestamp'][:19]
        action = activity['action']
        success = "✅" if activity['success'] else "❌"
        print(f"{success} {timestamp} - {action}")
        if activity['file_processed']:
            print(f"   📁 Archivo: {activity['file_processed']}")
        if activity['error_message']:
            print(f"   💥 Error: {activity['error_message']}")


def show_activity_summary():
    """Muestra un resumen de actividades por tipo."""
    manager = UserManager()

    activity_counts = {}
    success_counts = {}

    for activity in manager.activities:
        action = activity.action
        activity_counts[action] = activity_counts.get(action, 0) + 1
        if activity.success:
            success_counts[action] = success_counts.get(action, 0) + 1

    print(f"\n📊 **Resumen de Actividades:**")
    print("-" * 40)

    for action, count in sorted(activity_counts.items()):
        success_count = success_counts.get(action, 0)
        success_rate = (success_count / count) * 100 if count > 0 else 0

        action_emoji = {
            "bot_started": "🤖",
            "file_uploaded": "📁",
            "pdf_generated": "📄",
            "audio_generated": "🎵",
            "video_generated": "🎬",
            "status_checked": "📊",
            "stats_checked": "📈",
            "invalid_file_uploaded": "❌",
            "file_too_large": "📏",
            "text_extraction_failed": "📖",
            "pdf_processing_error": "💥",
            "generation_failed": "🎯"
        }.get(action, "📝")

        print(f"{action_emoji} {action}: {count} ({success_rate:.1f}% éxito)")


def main():
    """Función principal con menú interactivo."""
    while True:
        print("\n" + "=" * 50)
        print("🤖 **Panel de Administración del Bot**")
        print("=" * 50)
        print("1. 📊 Mostrar estadísticas generales")
        print("2. 👤 Mostrar detalles de usuario")
        print("3. 📋 Mostrar resumen de actividades")
        print("4. 📄 Exportar datos de usuario específico")
        print("5. 📁 Exportar datos de todos los usuarios")
        print("6. 🚪 Salir")

        choice = input("\nSelecciona una opción (1-6): ").strip()

        if choice == "1":
            show_bot_stats()

        elif choice == "2":
            try:
                user_id = int(input("Ingresa el ID del usuario: "))
                show_user_details(user_id)
            except ValueError:
                print("❌ ID de usuario inválido.")

        elif choice == "3":
            show_activity_summary()

        elif choice == "4":
            try:
                user_id = int(input("Ingresa el ID del usuario: "))
                export_user_data(user_id)
            except ValueError:
                print("❌ ID de usuario inválido.")

        elif choice == "5":
            export_user_data()

        elif choice == "6":
            print("👋 ¡Hasta luego!")
            break

        else:
            print("❌ Opción inválida. Intenta de nuevo.")


if __name__ == "__main__":
    main()
