#!/usr/bin/env python3
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_reflection_agent():
    print("Testing Reflection Agent...")
    print("="*60)
    
    user_id = "reflection-test-user"
    
    # 1. Create test conversation with multiple messages
    print("\n1. Creating test conversation...")
    conv_data = {
        "user_id": user_id,
        "title": "Test Reflection Conversation",
        "meta_data": {"test": "reflection"}
    }
    response = requests.post(f"{BASE_URL}/api/conversations", json=conv_data)
    conversation = response.json()
    conv_id = conversation["id"]
    print(f"Created conversation: {conv_id}")
    
    # 2. Send multiple messages to build conversation
    print("\n2. Building conversation with messages...")
    messages = [
        "Ahoj, volám sa Peter a pracujem ako programátor v Bratislave.",
        "Mám rád pizzu a kávu. Rád programujem v Pythone.",
        "Chcel by som sa naučiť viac o AI a machine learning.",
        "Môžeš mi odporučiť nejaké dobré zdroje na učenie?",
        "Ďakujem za pomoc! Zajtra začnem študovať."
    ]
    
    for i, msg in enumerate(messages):
        print(f"   Sending message {i+1}/{len(messages)}...")
        response = requests.post(f"{BASE_URL}/api/messages/chat", json={
            "conversation_id": conv_id,
            "content": msg,
            "model": "llama3.2"
        })
        if response.status_code != 200:
            print(f"   Error: {response.text}")
        time.sleep(2)  # Give time between messages
    
    # 3. Trigger manual summarization
    print("\n3. Triggering conversation summarization...")
    response = requests.post(f"{BASE_URL}/api/insights/conversation/{conv_id}/summarize")
    if response.status_code == 200:
        summary = response.json()
        print(f"Summary created!")
        print(f"   Summary: {summary['summary']}")
        print(f"   Key points: {', '.join(summary['key_points'])}")
        print(f"   Topics: {', '.join(summary['topics'])}")
        print(f"   Goals: {', '.join(summary['goals'])}")
        print(f"   Sentiment: {summary['sentiment']}")
    else:
        print(f"Error creating summary: {response.text}")
    
    # 4. Create second conversation
    print("\n4. Creating second conversation...")
    conv2_data = {
        "user_id": user_id,
        "title": "Another Test Conversation",
        "meta_data": {"test": "reflection2"}
    }
    response = requests.post(f"{BASE_URL}/api/conversations", json=conv2_data)
    conv2 = response.json()
    conv2_id = conv2["id"]
    
    # Add some messages
    messages2 = [
        "Potrebujem pomoc s projektom v Pythone.",
        "Ide o web aplikáciu používajúcu FastAPI.",
        "Chcem pridať autentifikáciu a databázu."
    ]
    
    for msg in messages2:
        response = requests.post(f"{BASE_URL}/api/messages/chat", json={
            "conversation_id": conv2_id,
            "content": msg,
            "model": "llama3.2"
        })
        time.sleep(1)
    
    # 5. Trigger user analysis
    print("\n5. Triggering user analysis for insights...")
    response = requests.post(f"{BASE_URL}/api/insights/user/{user_id}/analyze")
    if response.status_code == 200:
        insights = response.json()
        print(f"Found {len(insights)} insights:")
        for insight in insights:
            print(f"\n   Type: {insight['insight_type']}")
            print(f"   Content: {insight['content']}")
            print(f"   Confidence: {insight['confidence']:.2f}")
    else:
        print(f"Error analyzing user: {response.text}")
    
    # 6. Get recent summaries
    print("\n6. Getting recent summaries...")
    response = requests.get(f"{BASE_URL}/api/insights/summaries/recent?user_id={user_id}")
    if response.status_code == 200:
        summaries = response.json()
        print(f"Found {len(summaries)} summaries")
        for summ in summaries:
            print(f"   - {summ['conversation_id'][:8]}... : {summ['summary'][:50]}...")
    
    # 7. Search insights
    print("\n7. Searching insights for 'Python'...")
    response = requests.get(
        f"{BASE_URL}/api/insights/search/insights",
        params={"query": "Python", "user_id": user_id}
    )
    if response.status_code == 200:
        results = response.json()
        print(f"Found {len(results)} relevant insights")
        for result in results:
            print(f"   - {result['content'][:80]}...")

if __name__ == "__main__":
    test_reflection_agent()