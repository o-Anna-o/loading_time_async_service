# async_calculate_time/calculate/views.py

import logging
import time
import random
import requests

from concurrent import futures
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

# === CONFIG ===
CALLBACK_BASE_URL = "http://localhost:8080/api/request_ship"
AUTH_TOKEN = "12345678"

executor = futures.ThreadPoolExecutor(max_workers=2)


# =========================================================
# DOMAIN CALCULATION (полный аналог Go CalculateLoadingTime)
# =========================================================
def calculate_loading_time(
    containers_20ft: int,
    containers_40ft: int,
    ships: list
) -> float:
    """
    Формула полностью соответствует Go:

    total_cranes = sum(ship.cranes * ship.ships_count)
    loading_time = (20ft * 2 + 40ft * 3) / total_cranes
    """

    total_cranes = 0
    for ship in ships:
        cranes = ship.get("cranes", 0)
        count = ship.get("ships_count", 0)
        total_cranes += cranes * count

    if total_cranes == 0:
        return 0.0

    total_container_time = containers_20ft * 2 + containers_40ft * 3
    return total_container_time / total_cranes


# =========================================================
# ASYNC TASK
# =========================================================
def calculate_loading_time_task(calc_data: dict) -> dict:
    try:
        request_ship_id = calc_data.get("request_ship_id")
        containers_20ft = calc_data.get("containers_20ft", 0)
        containers_40ft = calc_data.get("containers_40ft", 0)
        ships = calc_data.get("ships", [])

        if not request_ship_id or not ships:
            return {
                "request_ship_id": request_ship_id,
                "success": False,
                "error_message": "invalid input data"
            }

        logger.info(f"Start async calc for request_ship_id={request_ship_id}")

        # обязательная задержка 5–10 сек
        time.sleep(random.uniform(5, 10))

        loading_time = calculate_loading_time(
            containers_20ft,
            containers_40ft,
            ships
        )

        # случайный результат
        if random.random() < 0.8:
            return {
                "request_ship_id": request_ship_id,
                "success": True,
                "loading_time": loading_time
            }

        return {
            "request_ship_id": request_ship_id,
            "success": False,
            "error_message": "calculation failed randomly"
        }

    except Exception as e:
        logger.exception("Async calculation error")
        return {
            "request_ship_id": calc_data.get("request_ship_id"),
            "success": False,
            "error_message": str(e)
        }


# =========================================================
# CALLBACK
# =========================================================
def callback_handler(task):
    result = task.result()
    request_ship_id = result.get("request_ship_id")

    if not request_ship_id:
        logger.error("Callback without request_ship_id")
        return

    url = f"{CALLBACK_BASE_URL}/{request_ship_id}/loading-time-result"

    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            url,
            json=result,
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            logger.info(f"Callback success for request_ship_id={request_ship_id}")
        else:
            logger.error(
                f"Callback failed [{response.status_code}]: {response.text}"
            )

    except requests.RequestException as e:
        logger.error(f"Callback network error: {e}")


# =========================================================
# API ENDPOINT (Go вызывает ТОЛЬКО его)
# =========================================================
@api_view(["POST"])
def calculate_loading_time_api(request):
    """
    POST /api/async/loading-time
    """

    required_fields = [
        "request_ship_id",
        "containers_20ft",
        "containers_40ft",
        "ships"
    ]

    for field in required_fields:
        if field not in request.data:
            return Response(
                {"error": f"{field} is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

    task = executor.submit(
        calculate_loading_time_task,
        request.data
    )
    task.add_done_callback(callback_handler)

    return Response(
        {"message": "loading time calculation started"},
        status=status.HTTP_200_OK
    )
