from app.handlers.gpt_handler import send_message_to_assistant
from app import db
from sqlalchemy.sql import text

def create_summary_for_thread(thread_id):
    """
    Создаёт саммери для всей истории переписки в рамках одного thread_id.
    """
    try:
        # Используем text() для выполнения SQL-запроса
        query = text(
            "SELECT role, content FROM messages WHERE thread_id = :thread_id ORDER BY id ASC"
        )
        messages = db.session.execute(query, {"thread_id": thread_id}).fetchall()

        # Формируем текст для саммери
        conversation_history = ""
        for role, content in messages:  # Итерируемся по кортежам
            role_name = "Пользователь" if role == "user" else "Ассистент"
            conversation_history += f"{role_name}: {content}\n"

        # Логируем историю переписки
        print(f"[LOG]: История переписки для thread_id {thread_id}:\n{conversation_history}")

        # Отправляем историю на саммери
        summary = send_message_to_assistant(
            f"Создайте краткое саммери не более 300 слов для следующей переписки:\n\n{conversation_history}"
        )

        # Ограничиваем саммери до 300 слов
        summary_words = summary.split()
        if len(summary_words) > 300:
            summary = " ".join(summary_words[:300]) + "..."

        # Логируем итоговый текст саммери
        print(f"[LOG]: Итоговый текст саммери для thread_id {thread_id}:\n{summary}")

        return summary

    except Exception as e:
        print(f"[ERROR]: Ошибка при создании саммери для thread_id {thread_id}: {e}")
        return None
from app.handlers.gpt_handler import send_message_to_assistant
from app import db
from sqlalchemy.sql import text

def create_summary_for_thread(thread_id):
    """
    Создаёт саммери для всей истории переписки в рамках одного thread_id.
    """
    try:
        # Используем text() для выполнения SQL-запроса
        query = text(
            "SELECT role, content FROM messages WHERE thread_id = :thread_id ORDER BY id ASC"
        )
        messages = db.session.execute(query, {"thread_id": thread_id}).fetchall()

        # Формируем текст для саммери
        conversation_history = ""
        for role, content in messages:  # Итерируемся по кортежам
            role_name = "Пользователь" if role == "user" else "Ассистент"
            conversation_history += f"{role_name}: {content}\n"

        # Логируем историю переписки
        print(f"[LOG]: История переписки для thread_id {thread_id}:\n{conversation_history}")

        # Отправляем историю на саммери
        summary = send_message_to_assistant(
            f"Создайте краткое саммери не более 300 слов для следующей переписки:\n\n{conversation_history}"
        )

        # Ограничиваем саммери до 300 слов
        summary_words = summary.split()
        if len(summary_words) > 300:
            summary = " ".join(summary_words[:300]) + "..."

        # Логируем итоговый текст саммери
        print(f"[LOG]: Итоговый текст саммери для thread_id {thread_id}:\n{summary}")

        return summary

    except Exception as e:
        print(f"[ERROR]: Ошибка при создании саммери для thread_id {thread_id}: {e}")
        return None
