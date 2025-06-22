import os
import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

try:
    model = genai.GenerativeModel("gemini-1.0-pro")
    response = model.generate_content("Hello, who are you?")
    print("RESPONSE:", response)
except Exception as e:
    print("ERROR:", e)
