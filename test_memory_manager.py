#!/usr/bin/env python3
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_memory_manager():
    print("Testing Long-term Memory Manager...")
    print("="*60)
    
    user_id = "memory-manager-test"
    
    # 1. Create first conversation
    print("\n1. Creating first conversation...")
    conv1_data = {
        "user_id": user_id,
        "title": "Conversation 1 - Pizza",
        "meta_data": {"test": "memory_manager"}
    }
    response = requests.post(f"{BASE_URL}/api/conversations", json=conv1_data)
    conv1 = response.json()
    conv1_id = conv1["id"]
    
    # 2. Ask about favorite food
    print("\n2. First conversation - asking about favorite food...")
    message1 = {
        "conversation_id": conv1_id,
        "content": "Aká je najlepšia pizza v Bratislave?",
        "model": "llama3.2"
    }
    response = requests.post(f"{BASE_URL}/api/messages/chat", json=message1)
    if response.status_code == 200:
        chat1 = response.json()
        print(f"User: {chat1['user_message']['content']}")
        print(f"AI: {chat1['assistant_message']['content'][:200]}...")
        print(f"Memory used: {chat1['memory_used']}, Is duplicate: {chat1['is_duplicate']}")
    
    # 3. Create second conversation
    print("\n3. Creating second conversation...")
    conv2_data = {
        "user_id": user_id,
        "title": "Conversation 2 - Same question",
        "meta_data": {"test": "memory_manager"}
    }
    response = requests.post(f"{BASE_URL}/api/conversations", json=conv2_data)
    conv2 = response.json()
    conv2_id = conv2["id"]
    
    # 4. Ask the SAME question in different conversation
    print("\n4. Second conversation - asking SAME question...")
    message2 = {
        "conversation_id": conv2_id,
        "content": "Aká je najlepšia pizza v Bratislave?",
        "model": "llama3.2"
    }
    response = requests.post(f"{BASE_URL}/api/messages/chat", json=message2)
    if response.status_code == 200:
        chat2 = response.json()
        print(f"User: {chat2['user_message']['content']}")
        print(f"AI: {chat2['assistant_message']['content'][:200]}...")
        print(f"Memory used: {chat2['memory_used']}, Is duplicate: {chat2['is_duplicate']}")
    
    # 5. Ask similar but different question
    print("\n5. Second conversation - asking SIMILAR question...")
    message3 = {
        "conversation_id": conv2_id,
        "content": "Kde nájdem dobrú pizzu v Bratislave?",
        "model": "llama3.2"
    }
    response = requests.post(f"{BASE_URL}/api/messages/chat", json=message3)
    if response.status_code == 200:
        chat3 = response.json()
        print(f"User: {chat3['user_message']['content']}")
        print(f"AI: {chat3['assistant_message']['content'][:200]}...")
        print(f"Memory used: {chat3['memory_used']}, Is duplicate: {chat3['is_duplicate']}")
    
    # 6. Create third conversation with different topic
    print("\n6. Creating third conversation - different topic...")
    conv3_data = {
        "user_id": user_id,
        "title": "Conversation 3 - Weather",
        "meta_data": {"test": "memory_manager"}
    }
    response = requests.post(f"{BASE_URL}/api/conversations", json=conv3_data)
    conv3 = response.json()
    conv3_id = conv3["id"]
    
    # 7. Ask about weather
    message4 = {
        "conversation_id": conv3_id,
        "content": "Aké bude počasie zajtra?",
        "model": "llama3.2"
    }
    response = requests.post(f"{BASE_URL}/api/messages/chat", json=message4)
    if response.status_code == 200:
        chat4 = response.json()
        print(f"User: {chat4['user_message']['content']}")
        print(f"AI: {chat4['assistant_message']['content'][:200]}...")
        print(f"Memory used: {chat4['memory_used']}, Is duplicate: {chat4['is_duplicate']}")
    
    # 8. Ask about pizza again to see if it remembers
    print("\n8. Third conversation - asking about pizza (should use memory)...")
    message5 = {
        "conversation_id": conv3_id,
        "content": "Mimochodom, aká je najlepšia pizza v Bratislave?",
        "model": "llama3.2"
    }
    response = requests.post(f"{BASE_URL}/api/messages/chat", json=message5)
    if response.status_code == 200:
        chat5 = response.json()
        print(f"User: {chat5['user_message']['content']}")
        print(f"AI: {chat5['assistant_message']['content'][:200]}...")
        print(f"Memory used: {chat5['memory_used']}, Is duplicate: {chat5['is_duplicate']}")
    
    print("\n" + "="*60)
    print("Memory Manager Test Complete!")

if __name__ == "__main__":
    test_memory_manager()