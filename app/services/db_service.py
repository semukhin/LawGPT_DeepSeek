"""
Сервис для работы с базой данных SQLite.
"""
import sqlite3
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

class DBService:
    """Сервис для работы с базой данных SQLite."""
    
    def __init__(self, db_file: str = 'scraped_content.db'):
        self.db_file = db_file
        self._create_tables()
        
    def _create_tables(self):
        """Создает необходимые таблицы в базе данных."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Таблица для хранения скрейпинга
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scraped_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                title TEXT,
                content TEXT,
                content_type TEXT,
                domain TEXT,
                scrape_date TIMESTAMP,
                status_code INTEGER,
                error TEXT
            )
        ''')
        
        # Таблица для хранения метаданных
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id INTEGER,
                key TEXT,
                value TEXT,
                FOREIGN KEY (content_id) REFERENCES scraped_content(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def url_exists(self, url: str) -> bool:
        """Проверяет, существует ли URL в базе данных."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM scraped_content WHERE url = ?", (url,))
        count = cursor.fetchone()[0]
        
        conn.close()
        return count > 0
        
    def save_content(self, content: Dict[str, Any]) -> bool:
        """Сохраняет результаты скрейпинга в базу данных."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Вставляем основной контент
            cursor.execute('''
                INSERT OR REPLACE INTO scraped_content 
                (url, title, content, content_type, domain, scrape_date, status_code, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                content['url'],
                content.get('title', ''),
                content.get('text', ''),
                content.get('content_type', 'text/html'),
                content.get('metadata', {}).get('domain', ''),
                datetime.now().isoformat(),
                content.get('status_code'),
                content.get('error')
            ))
            
            content_id = cursor.lastrowid
            
            # Вставляем метаданные
            metadata = content.get('metadata', {})
            for key, value in metadata.items():
                if key not in ['domain']:  # domain уже сохранен в основной таблице
                    cursor.execute('''
                        INSERT INTO content_metadata (content_id, key, value)
                        VALUES (?, ?, ?)
                    ''', (content_id, key, str(value)))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logging.error(f"Ошибка при сохранении в базу данных: {e}")
            return False
            
    def get_content(self, url: str) -> Optional[Dict[str, Any]]:
        """Получает контент из базы данных по URL."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Получаем основной контент
            cursor.execute("""
                SELECT id, url, title, content, content_type, domain, scrape_date, status_code, error
                FROM scraped_content 
                WHERE url = ?
            """, (url,))
            
            row = cursor.fetchone()
            if not row:
                return None
                
            content = {
                'id': row[0],
                'url': row[1],
                'title': row[2],
                'text': row[3],
                'content_type': row[4],
                'metadata': {
                    'domain': row[5],
                    'scrape_date': row[6],
                    'status_code': row[7]
                },
                'error': row[8]
            }
            
            # Получаем метаданные
            cursor.execute("""
                SELECT key, value 
                FROM content_metadata 
                WHERE content_id = ?
            """, (content['id'],))
            
            for key, value in cursor.fetchall():
                content['metadata'][key] = value
                
            conn.close()
            return content
            
        except Exception as e:
            logging.error(f"Ошибка при получении данных из базы: {e}")
            return None
            
    def delete_content(self, url: str) -> bool:
        """Удаляет контент из базы данных."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Получаем id контента
            cursor.execute("SELECT id FROM scraped_content WHERE url = ?", (url,))
            row = cursor.fetchone()
            if not row:
                return False
                
            content_id = row[0]
            
            # Удаляем метаданные
            cursor.execute("DELETE FROM content_metadata WHERE content_id = ?", (content_id,))
            
            # Удаляем основной контент
            cursor.execute("DELETE FROM scraped_content WHERE id = ?", (content_id,))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logging.error(f"Ошибка при удалении данных из базы: {e}")
            return False