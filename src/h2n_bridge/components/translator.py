from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

class Translator:
    def __init__(self):
        """
        Initializes the Groq client.
        Requires GROQ_API_KEY in .env file.
        """
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables.")
        
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"  # Updated from deprecated llama3-70b-8192

    def translate(self, text):
        """
        Translates Hebrew text to natural English using Groq LPU.
        Args:
            text (str): Input Hebrew text.
        Returns:
            str: Natural English translation.
        """
        if not text:
            return ""

        system_prompt = (
            "You are a professional Hebrew-to-English translator. "
            "Your goal is to convert the input Hebrew text into NATURAL, idiomatic American English. "
            "Do NOT translate word-for-word. Capture the intent, tone, and nuance. "
            "Output ONLY the English translation. No preamble or explanations."
        )

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                model=self.model,
                temperature=0.3, 
                max_tokens=1024,
            )
            return chat_completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"Translation Error: {e}", flush=True)
            return "[Error in Translation]"

if __name__ == "__main__":
    # Test
    # t = Translator()
    # print(t.translate("אני אבדוק ואחזור אליך"))
    pass
