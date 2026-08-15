import requests


def test_chat():
    # Attempt to login first to get the token
    token = None
    try:
        res = requests.post(
            "http://127.0.0.1:8000/api/auth/login",
            data={"username": "test@example.com", "password": "password123"},
        )
        token = res.json().get("access_token")
    except:
        pass

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        # Assuming the backend is running on 8000
        res = requests.post(
            "http://127.0.0.1:8000/api/chat/",
            json={"message": "Describe this image."},
            headers=headers,
        )
        print("Status Code:", res.status_code)
        print("Response:", res.text)
    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    test_chat()
