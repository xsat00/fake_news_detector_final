import os
from dotenv import load_dotenv
from bardapi import Bard

load_dotenv()

token = os.getenv("BARD_API_KEY")
if not token:
    raise ValueError("BARD_API_KEY not found in environment variables.")

bard = Bard(token=token)

def verify_with_bard(text: str) -> str:
    """
    Use Bard API to check if text is potentially fake or misleading.

    Args:
        text (str): News content to verify.

    Returns:
        str: Bard's response content or error message.
    """
    prompt = (
        "You are a fact-checking assistant. "
        "Is the following news content potentially fake or misleading? "
        "Reply briefly with 'Yes' or 'No' and explain why.\n\n"
        f"{text}"
    )
    try:
        response = bard.get_answer(prompt)
        return response['content']
    except Exception as e:
        return f"Bard Error: {e}"