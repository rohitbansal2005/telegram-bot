import google.generativeai as genai

genai.configure(api_key="AIzaSyDb7aKSLnJuoP5XTQtunjSxhnLjZ3KxqZk")

try:
    model = genai.GenerativeModel("gemini-1.0-pro")
    response = model.generate_content("Hello, who are you?")
    print("RESPONSE:", response)
except Exception as e:
    print("ERROR:", e)
