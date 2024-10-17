import os
from openai import OpenAI

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def send_openai_request(prompt: str) -> str:
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format="json",
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("OpenAI returned an empty response.")
    return content
