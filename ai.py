# ai.py — your first real call to Claude.
import os
from dotenv import load_dotenv
import anthropic

load_dotenv()                     # reads .env and loads your key into the environment
client = anthropic.Anthropic()    # the client auto-finds ANTHROPIC_API_KEY — no key in code

def ask_claude(prompt, system="You are a helpful assistant.", model="claude-haiku-4-5-20251001", max_tokens=300):
    """Send a prompt to Claude and return just the text of the reply."""
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,                                   # standing rules for Claude
        messages=[{"role": "user", "content": prompt}],  # the specific request
    )
    return message.content[0].text
    

# runs only with `python ai.py`
if __name__ == "__main__":
    reply = ask_claude("In one sentence, congratulate someone on their first ever API call.")
    print(reply)