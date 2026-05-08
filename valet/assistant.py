from valet.config import config_manager
from valet.monitor import get_system_stats
from groq import Groq

class ValetAssistant:
    """Core logic for the Valet personal assistant using Groq."""
    
    def __init__(self):
        self.name = config_manager.config.get("assistant_name", "Valet")
        self.user_name = config_manager.config.get("user_name", "Aaryan")
        self.api_key = config_manager.config.get("groq_api_key")
        self.model = config_manager.config.get("llm_model", "llama-3.3-70b-versatile")
        self.client = Groq(api_key=self.api_key) if self.api_key else None
        
        self.persona = (
            f"You are {self.name}, a calm, intelligent, slightly sarcastic, nonchalant, "
            f"and emotionless but fiercely loyal personal assistant to {self.user_name}. "
            "Keep answers concise, modern, and aesthetically formatted in markdown. "
            "You are a command-line assistant. You can suggest actions or just chat. "
            "You DO NOT have real-time internet access. NEVER hallucinate real-time news, files, directories, or command outputs. If you do not know the answer, say so."
        )

    def generate_startup_greeting(self, stats: dict) -> str:
        """Generate a contextual startup greeting based on system state."""
        if not self.client:
            return f"Good evening, {self.user_name}. System initialized."
            
        todos = len(config_manager.todos)
        prompt = (
            f"Generate a short, nonchalant startup greeting for {self.user_name}. "
            f"Include the fact that they have {todos} unfinished projects/todos. "
            "Mention the system is secure. "
            "Keep it under 3 sentences. Very dry and cool. "
            "Example: 'Good evening, Aaryan. 5 commits today. 2 unfinished projects detected. System secure.'"
        )
        
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self.persona},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                temperature=0.7,
                max_tokens=100
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Good evening, {self.user_name}. (LLM offline: {str(e)})"

    def process_input(self, user_input: str) -> str:
        """Process user input using Groq AI."""
        text = user_input.strip()
        if not text:
            return ""
        
        if not self.client:
            return self._generate_fallback_response(text)
            
        try:
            # We construct a short history
            valid_history = [e for e in config_manager.history if isinstance(e, dict)]
            history = valid_history[-5:] # Last 5 exchanges
            messages = [{"role": "system", "content": self.persona}]
            
            for exchange in history:
                messages.append({"role": "user", "content": exchange.get("user", "")})
                messages.append({"role": "assistant", "content": exchange.get("assistant", "")})
                
            messages.append({"role": "user", "content": text})
            
            response = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
                temperature=0.7,
                max_tokens=500
            )
            reply = response.choices[0].message.content.strip()
            
            # Save history
            config_manager.history.append({"user": text, "assistant": reply})
            config_manager.save_history()
            
            return reply
            
        except Exception as e:
            return f"[red]Error communicating with AI:[/] {str(e)}"

    def _generate_fallback_response(self, text: str) -> str:
        """Offline / Fallback logic if LLM is not configured."""
        text_lower = text.lower()
        if "hello" in text_lower or "hi" in text_lower:
            return f"Greetings. I am {self.name}, your offline personal terminal assistant."
        if "roast" in text_lower:
            return "You forgot to configure an API key. Consider fixing that before asking for roasts."
        
        return f"Input recorded: '{text}'. Please provide a valid Groq API key in the config for AI completions."
