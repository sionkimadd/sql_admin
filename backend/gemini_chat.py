from vertexai.preview.generative_models import GenerativeModel

class GeminiChat:
    def __init__(self):
        self.model = GenerativeModel("gemini-2.0-flash-lite-001")
    
    def get_response(self, user_message: str) -> str:
        try:
            prompt = f"""You are a MySQL database expert. 
            Provide clear and accurate answers to the user's questions.
            Your answers should be concise and relevant to the user's query.
            Include example queries whenever possible.

            User question: {user_message}"""
            
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f'Failed: {str(e)}' 