"""
Ollama client configured for Qwen 2.5 Coder.
Optimised prompts for code generation, explanation, and debugging using RAG context.
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class OllamaCoderClient:
    """
    Thin wrapper around the Ollama /api/generate endpoint
    using Qwen 2.5 Coder (7B — fits in 8 GB VRAM with Q4 quantisation).
    """

    def __init__(self):
        self.host = settings.CODING_OLLAMA_HOST
        self.model = settings.CODING_OLLAMA_MODEL
        self.timeout = settings.CODING_OLLAMA_TIMEOUT

    def check_connection(self) -> bool:
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=5)
            return r.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def check_model_available(self) -> bool:
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=5)
            if r.status_code == 200:
                names = [m.get('name', '') for m in r.json().get('models', [])]
                return self.model in names
            return False
        except requests.exceptions.RequestException:
            return False

    def generate(self, prompt: str, context: list[str] = None,
                 language: str = None, temperature: float = 0.2,
                 max_tokens: int = 2048) -> dict:
        """
        Generate a coding response.

        Args:
            prompt:      User's coding question or task description.
            context:     RAG-retrieved code chunks used as reference.
            language:    Programming language hint (optional).
            temperature: Lower = more deterministic code (default 0.2).
            max_tokens:  Max tokens to generate.

        Returns:
            dict with 'text', 'model', 'prompt_tokens', 'completion_tokens'.
        """
        full_prompt = self._build_code_prompt(prompt, context, language)
        logger.info(f"Code generation with {self.model} | lang={language or 'any'}")

        payload = {
            'model': self.model,
            'prompt': full_prompt,
            'stream': False,
            'options': {
                'temperature': temperature,
                'num_predict': max_tokens,
                'top_p': 0.9,
                'repeat_penalty': 1.1,
            },
        }

        try:
            r = requests.post(f"{self.host}/api/generate", json=payload, timeout=self.timeout)
            r.raise_for_status()
            result = r.json()
            text = result.get('response', '')
            logger.info(f"Generated {len(text)} chars of code response")
            return {
                'text': text,
                'model': self.model,
                'prompt_tokens': result.get('prompt_eval_count', 0),
                'completion_tokens': result.get('eval_count', 0),
                'total_duration_ms': result.get('total_duration', 0) // 1_000_000,
            }
        except requests.exceptions.Timeout:
            raise Exception("Qwen Coder request timed out — try a shorter prompt or reduce max_tokens.")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to reach Ollama: {e}")

    def _build_code_prompt(self, query: str, context: list[str] = None, language: str = None) -> str:
        lang_hint = f" ({language})" if language else ""
        system = (
            f"You are an expert software engineer and AI coding assistant{lang_hint}.\n"
            "Your task is to help developers write, understand, debug, and improve code.\n"
            "You have access to a code knowledge base retrieved below — use it as primary reference.\n\n"
            "Rules:\n"
            "1. Always provide correct, runnable code when asked to write code.\n"
            "2. Use the retrieved code context to match existing style, patterns, and APIs.\n"
            "3. Explain your reasoning briefly before or after code blocks.\n"
            "4. For bug fixes, identify the root cause first.\n"
            "5. Format code in fenced code blocks with the language identifier.\n"
            "6. If the context doesn't contain enough info, say so clearly.\n"
            "7. Prefer concise, idiomatic code over verbose solutions.\n"
        )

        parts = [system, "\n" + "=" * 64 + "\n"]

        if context:
            parts.append(f"### Retrieved Code Knowledge Base{lang_hint}:\n")
            for i, chunk in enumerate(context, 1):
                parts.append(f"--- [Snippet {i}] ---\n```{language or ''}\n{chunk.strip()}\n```\n")
            parts.append("=" * 64 + "\n")

        parts.append(f"### Developer Request:\n{query}\n")
        parts.append("=" * 64 + "\n")
        parts.append("### Response:\n")

        return "\n".join(parts)

    def pull_model(self) -> bool:
        try:
            r = requests.post(f"{self.host}/api/pull", json={'name': self.model}, timeout=600)
            r.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to pull {self.model}: {e}")
            return False


ollama_coder_client = OllamaCoderClient()
