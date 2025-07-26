#!/usr/bin/env python3
import requests
import json
import sys
import os
from datetime import datetime

BASE_URL = "http://localhost:8000"
USER_ID = os.getenv("USER_ID", "cli-user-default")
CONVERSATIONS_FILE = ".llm_conversations.json"

class LLMClient:
    def __init__(self):
        self.base_url = BASE_URL
        self.user_id = USER_ID
        self.current_conversation_id = None
        self.load_state()
    
    def load_state(self):
        """Load saved state from file"""
        if os.path.exists(CONVERSATIONS_FILE):
            with open(CONVERSATIONS_FILE, 'r') as f:
                state = json.load(f)
                self.current_conversation_id = state.get("current_conversation_id")
    
    def save_state(self):
        """Save current state to file"""
        state = {
            "current_conversation_id": self.current_conversation_id,
            "user_id": self.user_id
        }
        with open(CONVERSATIONS_FILE, 'w') as f:
            json.dump(state, f)
    
    def list_conversations(self):
        """List all conversations for current user"""
        response = requests.get(f"{self.base_url}/api/conversations/user/{self.user_id}")
        if response.status_code == 200:
            conversations = response.json()
            if not conversations:
                print("No conversations found.")
            else:
                print("\nYour conversations:")
                for i, conv in enumerate(conversations):
                    marker = "*" if conv["id"] == self.current_conversation_id else " "
                    print(f"{marker} [{i+1}] {conv['title'] or 'Untitled'} (ID: {conv['id'][:8]}...) - {conv['message_count']} messages")
        else:
            print(f"Error: {response.text}")
    
    def new_conversation(self, title=None):
        """Create a new conversation"""
        data = {
            "user_id": self.user_id,
            "title": title or f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        }
        response = requests.post(f"{self.base_url}/api/conversations", json=data)
        if response.status_code == 200:
            conversation = response.json()
            self.current_conversation_id = conversation["id"]
            self.save_state()
            print(f"Created new conversation: {conversation['title']}")
            return conversation["id"]
        else:
            print(f"Error creating conversation: {response.text}")
            return None
    
    def switch_conversation(self, index):
        """Switch to a different conversation by index"""
        response = requests.get(f"{self.base_url}/api/conversations/user/{self.user_id}")
        if response.status_code == 200:
            conversations = response.json()
            if 0 < index <= len(conversations):
                self.current_conversation_id = conversations[index-1]["id"]
                self.save_state()
                print(f"Switched to: {conversations[index-1]['title']}")
                self.show_recent_messages()
            else:
                print("Invalid conversation index")
        else:
            print(f"Error: {response.text}")
    
    def show_recent_messages(self, limit=5):
        """Show recent messages from current conversation"""
        if not self.current_conversation_id:
            print("No conversation selected")
            return
        
        response = requests.get(f"{self.base_url}/api/messages/conversation/{self.current_conversation_id}")
        if response.status_code == 200:
            messages = response.json()
            if messages:
                print(f"\nLast {min(limit, len(messages))} messages:")
                for msg in messages[-limit:]:
                    role = "You" if msg["role"] == "user" else "AI"
                    print(f"\n{role}: {msg['content']}")
                print("\n" + "-"*50)
        else:
            print(f"Error: {response.text}")
    
    def send_message(self, content):
        """Send a message in current conversation"""
        if not self.current_conversation_id:
            print("Creating new conversation...")
            if not self.new_conversation():
                return
        
        data = {
            "conversation_id": self.current_conversation_id,
            "content": content,
            "model": "llama3.2",
            "temperature": 0.7
        }
        
        print("Thinking...")
        response = requests.post(f"{self.base_url}/api/messages/chat", json=data)
        if response.status_code == 200:
            chat_response = response.json()
            print(f"\nAI: {chat_response['assistant_message']['content']}")
        else:
            print(f"Error: {response.text}")
    
    def search_messages(self, query):
        """Search messages in current conversation"""
        if not self.current_conversation_id:
            print("No conversation selected")
            return
        
        response = requests.get(
            f"{self.base_url}/api/messages/search/{self.current_conversation_id}",
            params={"query": query, "limit": 5}
        )
        if response.status_code == 200:
            results = response.json()
            if results:
                print(f"\nSearch results for '{query}':")
                for result in results:
                    print(f"\n[{result['role']}] {result['chunk_text']}")
                    print(f"Similarity: {result['similarity']:.2f}")
            else:
                print("No results found")
        else:
            print(f"Error: {response.text}")

def print_help():
    print("""
LLM Memory CLI Client

Commands:
  /new [title]     - Create new conversation
  /list           - List all conversations
  /switch <num>   - Switch to conversation by number
  /history        - Show recent messages
  /search <query> - Search in current conversation
  /help           - Show this help
  /quit           - Exit
  
Just type anything else to chat!
""")

def main():
    client = LLMClient()
    print("Welcome to LLM Memory CLI! Type /help for commands.")
    
    if client.current_conversation_id:
        print(f"Continuing previous conversation...")
        client.show_recent_messages(3)
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            
            if user_input.startswith("/"):
                parts = user_input.split(maxsplit=1)
                command = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""
                
                if command == "/quit":
                    print("Goodbye!")
                    break
                elif command == "/help":
                    print_help()
                elif command == "/new":
                    client.new_conversation(args if args else None)
                elif command == "/list":
                    client.list_conversations()
                elif command == "/switch":
                    if args.isdigit():
                        client.switch_conversation(int(args))
                    else:
                        print("Usage: /switch <number>")
                elif command == "/history":
                    client.show_recent_messages()
                elif command == "/search":
                    if args:
                        client.search_messages(args)
                    else:
                        print("Usage: /search <query>")
                else:
                    print(f"Unknown command: {command}")
            else:
                client.send_message(user_input)
        
        except KeyboardInterrupt:
            print("\nUse /quit to exit")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()