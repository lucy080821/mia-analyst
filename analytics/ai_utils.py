"""
AI Utility Module — Groq Wrapper.
Mocking Google's GenerativeModel interface so we don't break any existing code.
"""
import logging
import json
from django.conf import settings
from groq import Groq

logger = logging.getLogger(__name__)

class DummyPart:
    def __init__(self):
        self.text = "ok"

class DummyContent:
    def __init__(self):
        self.parts = [DummyPart()]

class DummyCandidate:
    def __init__(self):
        self.content = DummyContent()

class GroqResponseWrapper:
    def __init__(self, text: str):
        self.text = text
        self.candidates = [DummyCandidate()]

class GroqGenerativeModel:
    def __init__(self, model_name: str = None):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        # Override gemini model names to groq model names
        if not model_name or "gemini" in model_name.lower():
            self.model_name = getattr(settings, 'GROQ_MODEL_NAME', 'llama-3.3-70b-versatile')
        else:
            self.model_name = model_name

    def generate_content(self, prompt, generation_config=None):
        try:
            # Handle if prompt is a list (e.g. [system_prompt, "USER QUESTION: ..."])
            if isinstance(prompt, list):
                prompt_text = "\n\n".join(str(p) for p in prompt)
            else:
                prompt_text = str(prompt)

            messages = [{"role": "user", "content": prompt_text}]
            
            kwargs = {
                "model": self.model_name,
                "messages": messages,
                "temperature": 0.2, # Good default for analytics
            }

            # Map Gemini JSON config to Groq
            if generation_config and isinstance(generation_config, dict):
                if generation_config.get("response_mime_type") == "application/json":
                    kwargs["response_format"] = {"type": "json_object"}
                    # Groq requires the word 'json' in the prompt when using json_object mode
                    if "json" not in prompt_text.lower():
                        messages[0]["content"] += "\nReturn JSON."

            chat_completion = self.client.chat.completions.create(**kwargs)
            result_text = chat_completion.choices[0].message.content
            return GroqResponseWrapper(result_text)
            
        except Exception as e:
            logger.error(f"Groq API Error: {e}")
            raise e

def get_generative_model(model_name: str = None):
    """
    Returns a configured GroqGenerativeModel instance which mimics Gemini.
    """
    return GroqGenerativeModel(model_name)

