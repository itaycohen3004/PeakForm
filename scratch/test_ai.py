import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
key = os.getenv("GEMINI_API_KEY")
print(f"Key found: {key[:10]}...")

if not key:
    print("Error: No key in environment.")
else:
    try:
        genai.configure(api_key=key)
        print("Listing models:")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)
    except Exception as e:
        print(f"Error listing models: {e}")
