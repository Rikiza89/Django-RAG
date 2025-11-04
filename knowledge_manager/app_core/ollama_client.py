"""
Ollama Client for Local LLM Inference
Handles communication with Ollama API for Llama 3.2 3B
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """
    Client for interacting with local Ollama instance
    """
    
    def __init__(self):
        self.host = settings.OLLAMA_HOST
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT
    
    def check_connection(self):
        """
        Check if Ollama is running and accessible
        
        Returns:
            bool: True if connected, False otherwise
        """
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def check_model_available(self):
        """
        Check if the specified model is available
        
        Returns:
            bool: True if model is available, False otherwise
        """
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                return self.model in model_names
            return False
        except requests.exceptions.RequestException:
            return False
    
    def generate(self, prompt, context=None, system_prompt=None, temperature=0.7, max_tokens=1000):
        """
        Generate text using Ollama
        
        Args:
            prompt (str): User prompt
            context (list): List of context strings for RAG
            system_prompt (str): System prompt to guide model behavior
            temperature (float): Sampling temperature
            max_tokens (int): Maximum tokens to generate
        
        Returns:
            dict: Response with generated text and metadata
        """
        try:
            # Build the full prompt
            full_prompt = self._build_rag_prompt(prompt, context, system_prompt)
            
            logger.info(f"Generating response with Ollama model: {self.model}")
            
            # Prepare request
            payload = {
                'model': self.model,
                'prompt': full_prompt,
                'stream': False,
                'options': {
                    'temperature': temperature,
                    'num_predict': max_tokens,
                }
            }
            
            # Make request
            response = requests.post(
                f"{self.host}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            generated_text = result.get('response', '')
            
            logger.info(f"Generated {len(generated_text)} characters")
            
            return {
                'text': generated_text,
                'model': self.model,
                'prompt_tokens': result.get('prompt_eval_count', 0),
                'completion_tokens': result.get('eval_count', 0),
                'total_duration_ms': result.get('total_duration', 0) // 1_000_000,  # Convert ns to ms
            }
            
        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out")
            raise Exception("Request timed out. The model might be processing a complex query.")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama request failed: {str(e)}")
            raise Exception(f"Failed to generate response: {str(e)}")
    
    def _build_rag_prompt(self, query, context=None, system_prompt=None):
        """
        Build RAG prompt with context
        
        Args:
            query (str): User query
            context (list): List of context strings
            system_prompt (str): Optional system prompt
        
        Returns:
            str: Complete prompt
        """
        if system_prompt is None:
            system_prompt = """You are a helpful AI assistant for a knowledge management system. 
Your role is to answer questions based on the provided context from internal company documents.

Guidelines:
- Answer based primarily on the provided context
- If the context doesn't contain enough information, say so clearly
- Be concise and accurate
- Cite specific parts of the context when relevant
- If you're unsure, express uncertainty rather than guessing"""
        
        prompt_parts = [system_prompt, ""]
        
        if context:
            prompt_parts.append("CONTEXT FROM DOCUMENTS:")
            prompt_parts.append("=" * 50)
            for i, ctx in enumerate(context, 1):
                prompt_parts.append(f"\n[Document {i}]")
                prompt_parts.append(ctx)
                prompt_parts.append("")
            prompt_parts.append("=" * 50)
            prompt_parts.append("")
        
        prompt_parts.append(f"USER QUESTION: {query}")
        prompt_parts.append("")
        prompt_parts.append("ANSWER:")
        
        return "\n".join(prompt_parts)
    
    def chat(self, messages, temperature=0.7, max_tokens=1000):
        """
        Chat with the model (multi-turn conversation)
        
        Args:
            messages (list): List of message dicts with 'role' and 'content'
            temperature (float): Sampling temperature
            max_tokens (int): Maximum tokens to generate
        
        Returns:
            dict: Response with generated text and metadata
        """
        try:
            logger.info(f"Chat request with {len(messages)} messages")
            
            payload = {
                'model': self.model,
                'messages': messages,
                'stream': False,
                'options': {
                    'temperature': temperature,
                    'num_predict': max_tokens,
                }
            }
            
            response = requests.post(
                f"{self.host}/api/chat",
                json=payload,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            message = result.get('message', {})
            generated_text = message.get('content', '')
            
            return {
                'text': generated_text,
                'model': self.model,
                'prompt_tokens': result.get('prompt_eval_count', 0),
                'completion_tokens': result.get('eval_count', 0),
                'total_duration_ms': result.get('total_duration', 0) // 1_000_000,
            }
            
        except Exception as e:
            logger.error(f"Chat request failed: {str(e)}")
            raise
    
    def pull_model(self):
        """
        Pull/download the model if not available
        
        Returns:
            bool: True if successful
        """
        try:
            logger.info(f"Pulling model: {self.model}")
            
            payload = {'name': self.model}
            
            response = requests.post(
                f"{self.host}/api/pull",
                json=payload,
                timeout=600  # 10 minutes for model download
            )
            
            response.raise_for_status()
            return True
            
        except Exception as e:
            logger.error(f"Failed to pull model: {str(e)}")
            return False


# Singleton instance
ollama_client = OllamaClient()