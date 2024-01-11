import os
import openai

openai.api_key = os.environ.get('OPEN_AI_KEY')

class OpenAIHelper():
    def get_response(self, prompt: str) -> str:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."}, 
                    {"role": "user", "content": prompt}
                ]
            )
            return response
        except Exception as e:
            print(f"An error occurred: {e}")
            return ""