#!/usr/bin/env python3
"""
Jednoduchý chat klient pre LLM Memory systém
Použitie: python chat.py "Vaša správa"
"""
import requests
import sys
import json

BASE_URL = "http://localhost:8000"

def chat(message, user_id="cli-user"):
    """Pošle správu a vráti odpoveď"""
    response = requests.post(
        f"{BASE_URL}/api/messages/simple-chat",
        json={
            "content": message,
            "user_id": user_id
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        return data["response"]
    else:
        return f"Error: {response.text}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Použitie: python chat.py 'Vaša správa'")
        print("Príklad: python chat.py 'Ahoj, ako sa máš?'")
        sys.exit(1)
    
    message = " ".join(sys.argv[1:])
    response = chat(message)
    print(f"AI: {response}")