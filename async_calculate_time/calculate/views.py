import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

import time
import random
import requests
import json

from concurrent import futures

logger = logging.getLogger(__name__)


CALLBACK_URL = "http://localhost:8080/api/request_ship"

AUTH_TOKEN = "123456789"

executor = futures.ThreadPoolExecutor(max_workers=1)


async def calculate_loading_time(request_ship_id: int, containers_20ft: int, containers_40ft: int) -> float:
    """
    Функция расчета времени погрузки (аналогичная Go-версии)
    Возвращает: время погрузки в часах
    """
    # В реальной реализации здесь будет запрос к API Go сервиса для получения данных о заявке
    # Пока используем имитацию данных
    
    # Имитация получения данных о кораблях в заявке (в реальной реализации получаем через API)
    # Формат: [{'ship_id': id, 'ships_count': count, 'cranes': number_of_cranes}]
    ships_in_request = [
        {'ship_id': 1, 'ships_count': 2, 'cranes': 3},  # container_ship с 3 кранами
        {'ship_id': 2, 'ships_count': 1, 'cranes': 2}   # bulk_carrier с 2 кранами
    ]
    
    # Рассчитываем общее количество кранов
    total_cranes = 0
    for ship_info in ships_in_request:
        cranes_per_ship = ship_info['cranes']
        ships_count = ship_info['ships_count']
        total_cranes += cranes_per_ship * ships_count
    
    if total_cranes == 0:
        return 0.0
    
    # Общее время = (20ft * 2 + 40ft * 3) / количество кранов
    total_container_time = float(containers_20ft) * 2 + float(containers_40ft) * 3
    loading_time = total_container_time / float(total_cranes)
    
    return loading_time



# def health_check(request):
    """
    Health check endpoint для мониторинга
    """
    serializer = StatusResponseSerializer({
        'status': 'ok',
        'service': 'django-async-calculator',
        'timestamp': timezone.now()
    })
    
    return Response(serializer.data)

from typing import Tuple, Optional
import math

def calculate_loading_time_for_request(calc_data):
    """Расчет времени погрузки с обработкой ошибок"""
    try:
        logger.info(f"Начало расчета времени погрузки для request_ship_id={calc_data.get('request_ship_id')}")
        
        # Имитация задержки
        delay = random.uniform(5, 10)
        time.sleep(delay)
        
        # Извлечение данных
        request_ship_id = calc_data.get('request_ship_id')
        containers_20ft = calc_data.get('containers_20ft', 0)
        containers_40ft = calc_data.get('containers_40ft', 0)
        
        if not request_ship_id:
            return {
                "request_ship_id": request_ship_id,
                "success": False,
                "error_message": "Не указан ID заявки"
            }
        
        # Выполнение расчета
        loading_time = calculate_loading_time(request_ship_id, containers_20ft, containers_40ft)
        
        # Случайный успех/неуспех (имитация реальных условий)
        is_success = random.random() < 0.8
        
        if is_success:
            return {
                "request_ship_id": request_ship_id,
                "success": True,
                "loading_time": loading_time
            }
        else:
            return {
                "request_ship_id": request_ship_id,
                "success": False,
                "error_message": "Расчет завершился неудачно (случайная ошибка)"
            }
            
    except Exception as e:
        logger.error(f"Ошибка в calculate_loading_time_for_request: {e}")
        return {
            "request_ship_id": calc_data.get('request_ship_id'),
            "success": False,
            "error_message": f"Внутренняя ошибка сервера: {str(e)}"
        }


def calc_callback(task):
    """Callback функция для отправки результатов расчета времени погрузки в Go сервис"""
    try:
        # Получаем результат выполнения задачи
        result = task.result()
        logger.info(f"Результат расчета: {result}")
        
        # Проверяем, что результат содержит ожидаемые данные
        if not isinstance(result, dict):
            logger.error(f"Некорректный формат результата: {result}")
            return
            
        # Формируем данные для отправки в Go
        request_ship_id = result.get("request_ship_id")
        
        if not request_ship_id:
            logger.error("Не найден request_ship_id в результате")
            return
            
        # Определяем успешность расчета
        success = result.get("success", False)
        
        # Формируем тело запроса
        callback_data = {
            "request_ship_id": request_ship_id,
            "success": success,
            "token": AUTH_TOKEN  # Простая авторизация
        }
        
        # Добавляем результаты если расчет успешен
        if success and result.get("loading_time") is not None:
            callback_data.update({
                "loading_time": result["loading_time"]
            })
        else:
            # Добавляем сообщение об ошибке
            error_msg = result.get("error_message", "Расчет завершился неудачно")
            callback_data["error_message"] = error_msg
        
        # URL для callback (должен соответствовать Go сервису)
        # POST /api/request_ship/:id/completion
        callback_url = f"{CALLBACK_URL}/{request_ship_id}/completion"
        
        # Отправляем результаты в Go сервис
        headers = {
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Добавляем action в данные формы
        if success and result.get("loading_time") is not None:
            form_data = {
                "action": "complete"
            }
            # Добавляем loading_time в form_data
            callback_data.pop("loading_time", None)  # Удаляем из JSON данных
            form_data["loading_time"] = result["loading_time"]
        else:
            form_data = {
                "action": "reject"
            }
            # Добавляем сообщение об ошибке в form_data если нужно
            if "error_message" in callback_data:
                form_data["error_message"] = callback_data.pop("error_message")
        
        try:
            # Отправляем данные как форму (form data)
            response = requests.post(
                callback_url,
                data=form_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Callback успешно отправлен для request_ship_id={request_ship_id}")
            else:
                logger.error(f"Ошибка отправки callback: статус {response.status_code}, ответ: {response.text}")
                
        except requests.RequestException as e:
            logger.error(f"Ошибка сети при отправке callback: {e}")
            
    except futures.CancelledError:
        logger.warning("Задача расчета была отменена")
    except Exception as e:
        logger.error(f"Неожиданная ошибка в callback: {e}")
    


@api_view(['POST'])
def calculate_loading_time_api(request):
    # Ожидаем данные для расчета времени погрузки
    request_ship_id = request.data.get("request_ship_id")
    containers_20ft = request.data.get("containers_20ft", 0)
    containers_40ft = request.data.get("containers_40ft", 0)
    
    if not request_ship_id:
        return Response(
            {"error": "поле request_ship_id обязательно"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Подготавливаем данные для расчета
    calc_data = {
        "request_ship_id": request_ship_id,
        "containers_20ft": containers_20ft,
        "containers_40ft": containers_40ft
    }
    
    # Запускаем асинхронный расчет
    task = executor.submit(calculate_loading_time_for_request, calc_data)
    task.add_done_callback(calc_callback)
    
    return Response(
        {"message": "расчет времени погрузки начат!"},
        status=status.HTTP_200_OK
    )