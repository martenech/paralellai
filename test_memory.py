#!/usr/bin/env python3
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_memory():
    print("Testing LLM Memory System...")
    print("="*50)
    
    # 1. Create conversation
    print("\n1. Creating new conversation...")
    conv_data = {
        "user_id": "memory-test-user",
        "title": "Test pamäte",
        "meta_data": {"test": "memory"}
    }
    response = requests.post(f"{BASE_URL}/api/conversations", json=conv_data)
    conversation = response.json()
    conv_id = conversation["id"]
    print(f"Created conversation: {conv_id}")
    
    # 2. Send first message
    print("\n2. Sending first message...")
    message1 = {
        "conversation_id": conv_id,
        "content": "Ahoj, volám sa Peter a mám rád pizzu Margherita. Zapamätaj si to.",
        "model": "llama3.2"
    }
    response = requests.post(f"{BASE_URL}/api/messages/chat", json=message1)
    if response.status_code == 200:
        chat1 = response.json()
        print(f"User: {chat1['user_message']['content']}")
        print(f"AI: {chat1['assistant_message']['content']}")
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return
    
    # 3. Send second message
    print("\n3. Sending second message...")
    message2 = {
        "conversation_id": conv_id,
        "content": "Aké je moje obľúbené jedlo?",
        "model": "llama3.2"
    }
    response = requests.post(f"{BASE_URL}/api/messages/chat", json=message2)
    chat2 = response.json()
    print(f"User: {chat2['user_message']['content']}")
    print(f"AI: {chat2['assistant_message']['content']}")
    
    # 4. Test different conversation
    print("\n4. Creating second conversation...")
    conv_data2 = {
        "user_id": "memory-test-user",
        "title": "Druhá konverzácia",
        "meta_data": {"test": "memory2"}
    }
    response = requests.post(f"{BASE_URL}/api/conversations", json=conv_data2)
    conversation2 = response.json()
    conv_id2 = conversation2["id"]
    
    message3 = {
        "conversation_id": conv_id2,
        "content": "Ako sa volám a čo mám rád?",
        "model": "llama3.2"
    }
    response = requests.post(f"{BASE_URL}/api/messages/chat", json=message3)
    chat3 = response.json()
    print(f"User: {chat3['user_message']['content']}")
    print(f"AI (new conversation): {chat3['assistant_message']['content']}")
    
    # 5. Return to first conversation
    print("\n5. Returning to first conversation...")
    message4 = {
        "conversation_id": conv_id,
        "content": "Pamätáš si ako sa volám?",
        "model": "llama3.2"
    }
    response = requests.post(f"{BASE_URL}/api/messages/chat", json=message4)
    chat4 = response.json()
    print(f"User: {chat4['user_message']['content']}")
    print(f"AI: {chat4['assistant_message']['content']}")
    
    # 6. Test search
    print("\n6. Testing search in conversation...")
    response = requests.get(
        f"{BASE_URL}/api/messages/search/{conv_id}",
        params={"query": "pizza", "limit": 3}
    )
    if response.status_code == 200:
        results = response.json()
        print(f"Search results for 'pizza':")
        for result in results:
            print(f"  - [{result['role']}] {result['chunk_text'][:50]}... (similarity: {result['similarity']:.2f})")
    
    # 7. Show conversation list
    print("\n7. User conversations:")
    response = requests.get(f"{BASE_URL}/api/conversations/user/memory-test-user")
    conversations = response.json()
    for conv in conversations:
        print(f"  - {conv['title']} ({conv['message_count']} messages)")

if __name__ == "__main__":
    test_memory()