# loading_time_ship_async_service/loading_time/views.py

# cd loading_time_ship_async_service
# python manage.py runserver 0.0.0.0:8000

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

import random
import requests

# Функция "расчёта" 
def calculate_loading_time():
    return round(random.uniform(5, 10), 2)

# Функция отправки результата 
CALLBACK_URL = "http://localhost:8080/api/request_ship/"

def send_loading_time(request_id, loading_time):
    url = f"{CALLBACK_URL}{request_id}/completion"
    data = {
        "action": "complete",
        "loading_time": loading_time  # Если Go API не принимает loading_time, можно убрать
    }
    try:
        response = requests.post(url, data=data, timeout=5)
        response.raise_for_status()
        print(f"Successfully sent loading time for request {request_id}")
    except requests.RequestException as e:
        print(f"Failed to send loading time for request {request_id}: {e}")

@api_view(['POST'])
def set_status(request):
    if "pk" in request.data:
        request_id = request.data["pk"]

        loading_time = calculate_loading_time()
        send_loading_time(request_id, loading_time)

        return Response({"status": "ok", "loading_time": loading_time}, status=status.HTTP_200_OK)

    return Response({"error": "Missing 'pk' in request"}, status=status.HTTP_400_BAD_REQUEST)
