# api_client.py
# -*- coding: utf-8 -*-
import requests
import pandas as pd
from datetime import datetime
import streamlit as st


class SensorAPIClient:
    """Клиент для работы с API датчиков"""

    def __init__(self, base_url="http://5.129.248.80:8001"):
        self.base_url = base_url
        self.session = requests.Session()

    def get_all_sensors(self):
        """Получить список всех датчиков с их текущими значениями из API"""
        try:
            # Пробуем получить данные из API
            # Сначала проверим доступные эндпоинты
            endpoints = [
                "/api/sensors/current",
                "/api/values/latest",
                "/sensors",
                "/values"
            ]

            for endpoint in endpoints:
                try:
                    response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        st.success(f"Подключено к API: {endpoint}")
                        return self._parse_api_response(data)
                except:
                    continue

            # Если API не отвечает, используем тестовые данные
            st.warning("API недоступен, используются тестовые данные")
            return self._get_test_data()

        except Exception as e:
            st.error(f"Ошибка подключения к API: {e}")
            return self._get_test_data()

    def _parse_api_response(self, data):
        """Парсинг ответа API в единый формат"""
        installations = {}

        # Адаптируйте под реальную структуру API
        if isinstance(data, dict):
            if 'installations' in data:
                return data
            elif 'sensors' in data:
                # Группируем по installation_id
                for sensor in data['sensors']:
                    inst_id = sensor.get('installation_id', 1)
                    if inst_id not in installations:
                        installations[inst_id] = {
                            'id': inst_id,
                            'name': f"Установка {inst_id}",
                            'sensors': []
                        }
                    installations[inst_id]['sensors'].append(sensor)
                return {'installations': list(installations.values())}

        return self._get_test_data()

    def _get_test_data(self):
        """Тестовые данные для демонстрации"""
        test_data = {
            "installations": [
                {
                    "id": 1,
                    "name": "Установка 1",
                    "sensors": [
                        {"id": 1, "name": "Датчик 1", "value": 25.5, "unit": "°C", "status": "normal"},
                        {"id": 2, "name": "Датчик 2", "value": 75.0, "unit": "%", "status": "warning"},
                        {"id": 3, "name": "Датчик 3", "value": 120.3, "unit": "kPa", "status": "normal"},
                        {"id": 4, "name": "Датчик 4", "value": 300.0, "unit": "V", "status": "alarm"}
                    ]
                },
                {
                    "id": 2,
                    "name": "Установка 2",
                    "sensors": [
                        {"id": 5, "name": "Датчик 1", "value": 22.1, "unit": "°C", "status": "normal"},
                        {"id": 6, "name": "Датчик 2", "value": 85.0, "unit": "%", "status": "normal"},
                        {"id": 7, "name": "Датчик 3", "value": 101.2, "unit": "kPa", "status": "warning"},
                        {"id": 8, "name": "Датчик 4", "value": 280.0, "unit": "V", "status": "normal"}
                    ]
                },
                {
                    "id": 3,
                    "name": "Установка 3",
                    "sensors": [
                        {"id": 9, "name": "Датчик 1", "value": 32.0, "unit": "°C", "status": "alarm"},
                        {"id": 10, "name": "Датчик 2", "value": 65.0, "unit": "%", "status": "normal"},
                        {"id": 11, "name": "Датчик 3", "value": 108.5, "unit": "kPa", "status": "normal"},
                        {"id": 12, "name": "Датчик 4", "value": 230.0, "unit": "V", "status": "normal"}
                    ]
                }
            ]
        }
        return test_data

    def save_to_database(self, db_manager):
        """Сохранить данные из API в базу данных"""
        data = self.get_all_sensors()

        if not data or 'installations' not in data:
            return False

        saved_count = 0
        for installation in data['installations']:
            for sensor in installation['sensors']:
                # Сохраняем показания датчиков
                reading = {
                    'installation_id': installation['id'],
                    'sensor_id': sensor['id'],
                    'sensor_name': sensor['name'],
                    'value': sensor['value'],
                    'status': sensor.get('status', self._determine_status(sensor)),
                    'source_ts': datetime.now(),
                    'recorded_at': datetime.now()
                }

                # Вставка в БД
                try:
                    db_manager.save_sensor_reading(reading)
                    saved_count += 1
                except Exception as e:
                    print(f"Ошибка сохранения: {e}")

        return saved_count

    def _determine_status(self, sensor):
        """Определение статуса на основе значения"""
        value = sensor['value']
        normal_min = sensor.get('normal_min', 0)
        normal_max = sensor.get('normal_max', 100)

        if normal_min <= value <= normal_max:
            return 'normal'
        elif value < normal_min * 0.8 or value > normal_max * 1.2:
            return 'alarm'
        else:
            return 'warning'
