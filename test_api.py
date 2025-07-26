#!/usr/bin/env python3
import requests
import json

BASE_URL = "http://localhost:8000"

def test_api():
    print("Testing API...")
    
    # 1. Health check
    print("\n1. Health check:")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # 2. Create conversation
    print("\n2. Creating conversation:")
    conv_data = {
        "user_id": "test-user-123",
        "title": "Test konverzácia",
        "meta_data": {"purpose": "testing"}
    }
    response = requests.post(f"{BASE_URL}/api/conversations", json=conv_data)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        conversation = response.json()
        print(f"Response: {json.dumps(conversation, indent=2)}")
        conv_id = conversation["id"]
        
        # 3. Send message
        print("\n3. Sending message:")
        message_data = {
            "conversation_id": conv_id,
            "content": "Ahoj, ako sa máš? Povedz mi niečo o Slovensku.",
            "model": "llama3.2",
            "temperature": 0.7
        }
        response = requests.post(f"{BASE_URL}/api/messages/chat", json=message_data)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            chat_response = response.json()
            print(f"User: {chat_response['user_message']['content']}")
            print(f"Assistant: {chat_response['assistant_message']['content']}")
            
            # 4. Get conversation messages
            print("\n4. Getting conversation history:")
            response = requests.get(f"{BASE_URL}/api/messages/conversation/{conv_id}")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                messages = response.json()
                print(f"Messages count: {len(messages)}")
                for msg in messages:
                    print(f"- {msg['role']}: {msg['content'][:100]}...")
        else:
            print(f"Error: {response.text}")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    test_api()