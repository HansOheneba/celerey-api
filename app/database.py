from app import get_db_connection
from datetime import datetime


class DBHelper:
    @staticmethod
    def execute_query(
        query, params=None, fetch_one=False, fetch_all=False, lastrowid=False
    ):
        """Execute SQL query and return results"""
        connection = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(query, params or ())

            if fetch_one:
                result = cursor.fetchone()
            elif fetch_all:
                result = cursor.fetchall()
            elif lastrowid:
                result = cursor.lastrowid
            else:
                result = None

            if not fetch_one and not fetch_all and not lastrowid:
                connection.commit()

            cursor.close()
            return result

        except Exception as e:
            if connection:
                connection.rollback()
            raise e
        finally:
            if connection:
                connection.close()

    @staticmethod
    def format_datetime(dt):
        """Format datetime object to string"""
        if dt:
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        return None

    @staticmethod
    def format_date(dt):
        """Format datetime object to date string only"""
        if dt:
            return dt.strftime("%Y-%m-%d")
        return None

    @staticmethod
    def parse_datetime(dt_str):
        """Parse datetime string to datetime object"""
        if dt_str:
            try:
                return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return datetime.strptime(dt_str, "%Y-%m-%d")
        return None

    @staticmethod
    def parse_date(date_str):
        """Parse date string to datetime object"""
        if date_str:
            return datetime.strptime(date_str, "%Y-%m-%d")
        return None
