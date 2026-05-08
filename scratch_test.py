from valet.assistant import ValetAssistant
from valet.config import config_manager
import sys

def main():
    assistant = ValetAssistant()
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "whats going on around the world"
        
    print(f"Query: {query}")
    print(f"Assistant Name: {assistant.name}")
    print(f"API Key present: {bool(assistant.client)}")
    print(f"Model: {assistant.model}")
    print("Response:")
    print(assistant.process_input(query))

if __name__ == "__main__":
    main()
