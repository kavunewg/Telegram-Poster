"""
Базовый репозиторий с общими методами
"""
from core.database import execute_query, execute_insert, execute_update, fetch_one, fetch_all


class BaseRepository:
    """Базовый класс для всех репозиториев"""
    
    def __init__(self, table_name: str):
        self.table_name = table_name
    
    def get_all(self, limit: int = 100, offset: int = 0) -> list:
        """Получить все записи"""
        sql = f"SELECT * FROM {self.table_name} LIMIT ? OFFSET ?"
        return execute_query(sql, (limit, offset))
    
    def get_by_id(self, record_id: int, user_id: int = None) -> dict:
        """Получить запись по ID"""
        if user_id:
            sql = f"SELECT * FROM {self.table_name} WHERE id = ? AND user_id = ?"
            result = execute_query(sql, (record_id, user_id))
        else:
            sql = f"SELECT * FROM {self.table_name} WHERE id = ?"
            result = execute_query(sql, (record_id,))
        return result[0] if result else None
    
    def create(self, data: dict) -> int:
        """Создать запись"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        sql = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"
        return execute_insert(sql, tuple(data.values()))
    
    def update(self, record_id: int, data: dict, user_id: int = None) -> bool:
        """Обновить запись"""
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        
        if user_id:
            sql = f"UPDATE {self.table_name} SET {set_clause} WHERE id = ? AND user_id = ?"
            params = tuple(data.values()) + (record_id, user_id)
        else:
            sql = f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?"
            params = tuple(data.values()) + (record_id,)
        
        rows_affected = execute_update(sql, params)
        return rows_affected > 0
    
    def delete(self, record_id: int, user_id: int = None) -> bool:
        """Удалить запись"""
        if user_id:
            sql = f"DELETE FROM {self.table_name} WHERE id = ? AND user_id = ?"
            rows_affected = execute_update(sql, (record_id, user_id))
        else:
            sql = f"DELETE FROM {self.table_name} WHERE id = ?"
            rows_affected = execute_update(sql, (record_id,))
        
        return rows_affected > 0
    
    def count(self, filters: dict = None) -> int:
        """Подсчитать количество записей"""
        sql = f"SELECT COUNT(*) as count FROM {self.table_name}"
        params = []
        
        if filters:
            conditions = ' AND '.join([f"{k} = ?" for k in filters.keys()])
            sql += f" WHERE {conditions}"
            params = list(filters.values())
        
        result = execute_query(sql, tuple(params) if params else None)
        return result[0]['count'] if result else 0