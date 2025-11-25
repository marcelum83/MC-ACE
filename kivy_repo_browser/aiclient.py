import os
import requests

class AIClient:
    def __init__(self, api_key, provider="openai", model=None):
        self.api_key = api_key
        self.provider = provider.lower()

        if self.provider == "openai":
            self.model = model or "gpt-3.5-turbo"
            self.url = "https://api.openai.com/v1/chat/completions"
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

        elif self.provider == "gemini":
            self.model = model or "gemini-1.5-flash-latest"
            self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
            self.headers = {"Content-Type": "application/json"}

        else:
            raise ValueError("Provider must be 'openai' or 'gemini'")

    def chat(self, message, model=None):
        if self.provider == "openai":
            payload = {
                "model": model or self.model,
                "messages": [{"role": "user", "content": message}],
            }
            r = requests.post(self.url, headers=self.headers, json=payload)
            r.raise_for_status()
            response = r.json()
            try:
                return response["choices"][0]["message"]["content"]
            except (KeyError, IndexError):
                print(f"Error: Invalid response format from OpenAI API: {response}")
                return ""

        elif self.provider == "gemini":
            payload = {
                "contents": [
                    {"parts": [{"text": message}]}
                ]
            }
            r = requests.post(self.url, headers=self.headers, json=payload)
            r.raise_for_status()
            response = r.json()
            try:
                return response["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError):
                print(f"Error: Invalid response format from Gemini API: {response}")
                return ""

if __name__ == '__main__':
    api_key = os.environ.get("AICI_API_KEY")
    if not api_key:
        print("Error: AICI_API_KEY environment variable not set.")
    else:
        client = AIClient(api_key, provider="gemini")
        prompt = "Tell me a joke."
        response = client.chat(prompt)
        print("response", response)
