import os
from openai import OpenAI

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def send_openai_request(prompt: str, custom_prompt: str = None) -> str:
    if custom_prompt:
        final_prompt = f"{custom_prompt}\n\n{prompt}"
    else:
        final_prompt = prompt

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": final_prompt}],
        response_format={"type": "text"},
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("OpenAI returned an empty response.")
    return content
