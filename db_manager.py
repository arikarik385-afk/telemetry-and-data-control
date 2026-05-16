# db_manager.py
# -*- coding: utf-8 -*-
import psycopg2
import psycopg2.extras
import pandas as pd
from datetime import datetime
import streamlit as st


class DatabaseManager:
    def __init__(self):
        # Параметры подключения - без специальных символов
        self.conn_params = {
            'host': 'localhost',
            'port': 5432,
            'database': 'data',  # имя вашей базы
            'user': 'postgres',
            'password': '1234'
        }

    def get_connection(self):
        """Получить соединение с БД"""
        try:
            conn = psycopg2.connect(**self.conn_params)
            return conn
        except Exception as e:
            st.error(f"Ошибка подключения к БД: {e}")
            return None

    def get_latest_sensor_values(self):
        """Получить последние значения всех датчиков"""
        conn = self.get_connection()
        if not conn:
            return pd.DataFrame()

        try:
            query = """
                SELECT DISTINCT ON (installation_id, sensor_id) 
                    installation_id,
                    sensor_id,
                    sensor_name,
                    value,
                    status,
                    recorded_at as timestamp
                FROM sensor_readings
                ORDER BY installation_id, sensor_id, recorded_at DESC
            """
            df = pd.read_sql(query, conn)

            if not df.empty:
                df['installation_name'] = df['installation_id'].apply(lambda x: f"Installation {x}")

            return df
        except Exception as e:
            st.error(f"Ошибка запроса: {e}")
            return pd.DataFrame()
        finally:
            conn.close()

    def get_events(self, from_date=None, to_date=None, sensor_ids=None):
        """Получить события"""
        conn = self.get_connection()
        if not conn:
            return pd.DataFrame()

        try:
            query = """
                SELECT 
                    id,
                    event_ts as timestamp,
                    installation_id,
                    sensor_id,
                    event_type as severity,
                    short_text as message,
                    details
                FROM events
                WHERE 1=1
            """
            params = []

            if from_date:
                query += " AND event_ts >= %s"
                params.append(from_date)
            if to_date:
                query += " AND event_ts <= %s"
                params.append(to_date)

            query += " ORDER BY event_ts DESC LIMIT 500"

            df = pd.read_sql(query, conn, params=params)

            if not df.empty:
                df['installation_name'] = df['installation_id'].apply(lambda x: f"Installation {x}")
                # Получаем названия датчиков
                try:
                    cursor = conn.cursor()
                    cursor.execute("SELECT DISTINCT sensor_id, sensor_name FROM sensor_readings")
                    sensors = {row[0]: row[1] for row in cursor.fetchall()}
                    df['sensor_name'] = df['sensor_id'].map(sensors).fillna(f"Sensor {df['sensor_id']}")
                except:
                    df['sensor_name'] = df['sensor_id'].apply(lambda x: f"Sensor {x}")

            return df
        except Exception as e:
            st.error(f"Ошибка запроса событий: {e}")
            return pd.DataFrame()
        finally:
            conn.close()

    def export_events_to_excel(self, from_date, to_date):
        """Экспорт событий в Excel"""
        events_df = self.get_events(from_date, to_date)
        return events_df

    def save_sensor_reading(self, reading):
        """Сохранить показание датчика"""
        conn = self.get_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            query = """
                INSERT INTO sensor_readings 
                (installation_id, sensor_id, sensor_name, value, status, source_ts, recorded_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                reading['installation_id'],
                reading['sensor_id'],
                reading['sensor_name'],
                reading['value'],
                reading['status'],
                reading.get('source_ts', datetime.now()),
                datetime.now()
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка сохранения: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
