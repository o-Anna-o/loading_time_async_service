import requests

CALLBACK_URL = "http://localhost:8080/api/request_ship/async_result"

def send_loading_time(request_id, loading_time):
    payload = {
        "request_id": request_id,
        "loading_time": loading_time,
        "token": "ASYNC2025"
    }
    requests.post(CALLBACK_URL, json=payload, timeout=3)