import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.security import create_access_token
import requests

def test():
    # Create valid token
    token = create_access_token(data={"sub": "testuser@example.com"})
    headers = {"Authorization": f"Bearer {token}"}
    
    # Try voice message
    print("Voice message:")
    voice_msg = "Describe this image.\n\n[System Instruction: You are responding via Text-to-Speech using the voice model \"\". You MUST reply entirely in the primary language associated with this voice model (e.g., if it is a Korean voice, reply entirely in Korean). Do not use English unless necessary.]"
    res2 = requests.post("http://127.0.0.1:8000/api/chat/", json={"message": voice_msg}, headers=headers)
    print(res2.status_code)
    print(res2.text)

if __name__ == "__main__":
    test()
