
import requests

res = requests.post(
    "http://localhost:8000/api/chat/",
    json={"message": "Hello", "session_id": 1},
    headers={
        # need an auth token if the endpoint is protected
    },
)
print(res.status_code)
print(res.text)
