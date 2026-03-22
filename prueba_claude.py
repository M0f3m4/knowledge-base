import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

respuesta = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=100,
    messages=[{"role": "user", "content": "Responde solo con JSON: {\"status\": \"ok\", \"mensaje\": \"Claude funcionando\"}"}]
)

print(respuesta.content[0].text)