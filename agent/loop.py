from dotenv import load_dotenv
load_dotenv()

import anthropic
client = anthropic.Anthropic()

from tools import TOOLS

def run():
    messages = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):  # Ctrl+C, Ctrl+D
            print("\nbye")
            break

        if user_input.lower() in ("exit", "quit"):
            break
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})

        response = client.messages.create(
            model = "claude-opus-5-5",
            max_tokens = 1024,
            tools=TOOLS,
            messages = messages
        )
        messages.append({"role": "assistant", "content": response.content})

        for block in response.content:
            if block.type == "text":
                print("Claude:", block.text)

if __name__ == "__main__":
    run()