# ai.py — your first real call to Claude.
import os
from dotenv import load_dotenv
import anthropic

load_dotenv()                     # reads .env and loads your key into the environment
client = anthropic.Anthropic()    # the client auto-finds ANTHROPIC_API_KEY — no key in code

class AIError(RuntimeError):
    """A Claude API failure translated to plain English. Raised instead of the raw
    anthropic exception so Streamlit's red error box leads with a sentence a human
    can act on ("add funds", "check your key") instead of SDK internals."""
    pass

def ask_claude(prompt, system="You are a helpful assistant.", model="claude-haiku-4-5-20251001", max_tokens=300):
    """Send a prompt to Claude and return just the text of the reply."""
    try:
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,                                   # standing rules for Claude
            messages=[{"role": "user", "content": prompt}],  # the specific request
        )
    except anthropic.AuthenticationError:
        raise AIError("The Claude API rejected your key — check ANTHROPIC_API_KEY in your "
                      ".env file (get a key at console.anthropic.com/settings/keys).") from None
    except anthropic.RateLimitError as e:
        wait = ""
        try:
            wait = e.response.headers.get("retry-after", "")
        except Exception:
            pass
        raise AIError("Hit the Claude API rate limit — wait "
                      f"{wait or 'a few'} seconds and try again.") from None
    except anthropic.BadRequestError as e:
        if "credit balance" in str(e).lower():
            raise AIError("Your Anthropic API key is out of credit — add funds at "
                          "console.anthropic.com/settings/billing.") from None
        raise
    except anthropic.APIConnectionError:
        raise AIError("Couldn't reach the Claude API — check your internet "
                      "connection and try again.") from None
    return message.content[0].text
    

# runs only with `python ai.py`
if __name__ == "__main__":
    reply = ask_claude("In one sentence, congratulate someone on their first ever API call.")
    print(reply)