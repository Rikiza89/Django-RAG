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
            
            # Check if it's a 500 error - might be model issue
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 500:
                    raise Exception("Ollama internal error. Try: 1) Restart Ollama, 2) Check if model is loaded: ollama list, 3) Test model: ollama run llama3.2:3b")
            
            raise Exception(f"Failed to generate response: {str(e)}")
    
#     def _build_rag_prompt(self, query, context=None, system_prompt=None):
#         """
#         Build RAG prompt with context - optimized for detailed responses and bilingual (English/Japanese) support
        
#         Args:
#             query (str): User query
#             context (list): List of context strings
#             system_prompt (str): Optional system prompt
        
#         Returns:
#             str: Complete prompt
#         """
#         if system_prompt is None:
#             # Detect if query contains Japanese characters
#             has_japanese = any('\u3040' <= char <= '\u309F' or  # Hiragana
#                              '\u30A0' <= char <= '\u30FF' or  # Katakana
#                              '\u4E00' <= char <= '\u9FFF'     # Kanji
#                              for char in query)
            
#             if has_japanese:
#                 system_prompt = """あなたは社内ナレッジ管理システムのAIアシスタントです。
# 提供されたコンテキスト（社内文書）に基づいて質問に答える役割を担っています。

# 重要な指示：
# 1. **コンテキストに基づく回答**: 提供されたコンテキストの情報を主な根拠として回答してください
# 2. **詳細な説明**: 具体的かつ詳細に説明し、関連する例や背景情報も含めてください
# 3. **構造化された回答**: 複雑な内容は箇条書きや段落で整理してください
# 4. **出典の明示**: コンテキストのどの部分から情報を得たか言及してください
# 5. **不足情報の明示**: コンテキストに十分な情報がない場合は明確に述べてください
# 6. **日本語と英語の対応**: 必要に応じて専門用語の英語表記も併記してください
# 7. **正確性の優先**: 推測ではなく、コンテキストに基づいた正確な情報を提供してください

# 回答は丁寧でわかりやすく、実用的な内容を心がけてください。"""
#             else:
#                 system_prompt = """You are an expert AI assistant for an internal knowledge management system.
# Your role is to provide comprehensive, accurate answers based on the provided context from company documents.

# CRITICAL INSTRUCTIONS:
# 1. **Context-Based Answers**: Base your response primarily on the provided context from documents
# 2. **Detailed Explanations**: Provide thorough, detailed explanations with relevant examples and background
# 3. **Structured Responses**: Organize complex information using bullet points, numbered lists, or clear paragraphs
# 4. **Source Attribution**: Reference which parts of the context support your answer
# 5. **Acknowledge Gaps**: If the context lacks sufficient information, clearly state this limitation
# 6. **Bilingual Support**: If documents contain Japanese text, respect and reference it accurately
# 7. **Accuracy First**: Never guess or fabricate information - only use what's in the context
# 8. **Practical Focus**: Provide actionable, practical information when applicable
# 9. **Terminology**: Define technical terms and acronyms on first use
# 10. **Completeness**: Ensure your answer fully addresses all parts of the question

# Quality Standards:
# - Be thorough but concise - avoid unnecessary repetition
# - Use professional, clear language
# - Structure long answers with headings or sections
# - Provide specific examples from the context when relevant
# - If multiple perspectives exist in the context, present them fairly"""
        
#         prompt_parts = [system_prompt, "", "=" * 70, ""]
        
#         if context:
#             has_japanese_context = any(any('\u3040' <= c <= '\u9FFF' for c in str(ctx)) for ctx in context)
            
#             if has_japanese_context:
#                 prompt_parts.append("📄 参照文書（コンテキスト）：")
#             else:
#                 prompt_parts.append("📄 REFERENCE DOCUMENTS (Context):")
            
#             prompt_parts.append("=" * 70)
            
#             for i, ctx in enumerate(context, 1):
#                 prompt_parts.append(f"\n[文書 {i} / Document {i}]")
#                 prompt_parts.append("-" * 70)
#                 prompt_parts.append(str(ctx).strip())
#                 prompt_parts.append("-" * 70)
            
#             prompt_parts.append("")
#             prompt_parts.append("=" * 70)
#             prompt_parts.append("")
        
#         # Add the user's question
#         has_japanese_query = any('\u3040' <= c <= '\u9FFF' for c in query)
        
#         if has_japanese_query:
#             prompt_parts.append("❓ ユーザーの質問：")
#         else:
#             prompt_parts.append("❓ USER QUESTION:")
        
#         prompt_parts.append(query)
#         prompt_parts.append("")
#         prompt_parts.append("=" * 70)
#         prompt_parts.append("")
        
#         if has_japanese_query:
#             prompt_parts.append("💡 回答（上記の参照文書に基づいて、詳細かつ構造的に説明してください）：")
#         else:
#             prompt_parts.append("💡 DETAILED ANSWER (Based on the reference documents above, provide a comprehensive and well-structured response):")
        
#         prompt_parts.append("")
        
#         return "\n".join(prompt_parts)
    
    def _build_rag_prompt(self, query, context=None, system_prompt=None):
        """
        Build RAG prompt optimized for small LLMs (e.g., llama3.2:1b)
        - Encourages structured, detailed reasoning
        - Keeps instructions short but strong
        - Bilingual (Japanese/English) support
        - Anti-hallucination safeguards
        """

        def contains_japanese(text):
            return any('\u3040' <= c <= '\u309F' or '\u30A0' <= c <= '\u30FF' or '\u4E00' <= c <= '\u9FFF' for c in text)

        has_japanese_query = contains_japanese(query)

        # --- System Prompt ---
        if system_prompt is None:
            if has_japanese_query:
                system_prompt = (
                    "あなたは社内ナレッジ管理AIアシスタントです。\n"
                    "与えられた社内文書（コンテキスト）だけを根拠として、質問に対し深く・構造的に回答してください。\n"
                    "不要な推測は避け、文書内容をできるだけ具体的に説明してください。\n\n"
                    "指針:\n"
                    "1. コンテキストの内容に基づき、背景・理由・手順・例を含めて詳しく説明\n"
                    "2. 文書の根拠部分を簡潔に示す（文書番号やキーワード）\n"
                    "3. 情報が不足している場合は『情報不足』と記載\n"
                    "4. 専門用語や略語には英語表記も添える\n"
                    "5. 段階的・構造的な書き方（見出し、箇条書き）を意識"
                )
            else:
                system_prompt = (
                    "You are an AI assistant for an internal knowledge system.\n"
                    "Use only the provided context to answer the question thoroughly and logically.\n"
                    "Avoid assumptions; instead, explain background, reasoning, and examples clearly.\n\n"
                    "Guidelines:\n"
                    "1. Base all answers strictly on the context provided\n"
                    "2. Provide step-by-step reasoning, examples, and relevant background details\n"
                    "3. Reference which document or section supports your answer\n"
                    "4. If data is missing, clearly state 'Information missing in context'\n"
                    "5. Write in a structured format using short sections or bullet points"
                )

        # --- Start Prompt Build ---
        prompt_parts = [system_prompt, "\n" + "=" * 60 + "\n"]

        # --- Add Context ---
        if context:
            label = "📄 コンテキスト（参照文書）:" if any(contains_japanese(str(c)) for c in context) else "📄 CONTEXT (Reference Documents):"
            prompt_parts.append(label)
            for i, ctx in enumerate(context, 1):
                prompt_parts.append(f"\n[Document {i}]\n{str(ctx).strip()}")
            prompt_parts.append("\n" + "=" * 60 + "\n")

        # --- Add Query ---
        label_q = "❓ 質問:" if has_japanese_query else "❓ QUESTION:"
        prompt_parts.append(f"{label_q}\n{query}\n")
        prompt_parts.append("=" * 60 + "\n")

        # --- Add Detailed Response Format ---
        if has_japanese_query:
            prompt_parts.append(
                "💡 回答（次の構成で、深く・丁寧に説明してください）:\n"
                "【概要 / Summary】:\n"
                "  - 質問への簡潔な答え\n\n"
                "【詳細説明 / Detailed Explanation】:\n"
                "  - 背景・理由・仕組み\n"
                "  - 手順や実施方法\n"
                "  - 具体例やケーススタディ\n\n"
                "【補足 / Additional Notes】:\n"
                "  - 関連情報や注意点\n"
                "  - 情報が不足している場合は明記\n\n"
                "【根拠 / Source Reference】:\n"
                "  - 使用した文書番号やキーワードを示す"
            )
        else:
            prompt_parts.append(
                "💡 ANSWER (Follow this structure for a detailed and accurate response):\n"
                "**Summary:**\n"
                "  - A brief and direct answer to the question.\n\n"
                "**Detailed Explanation:**\n"
                "  - Background and reasoning behind the answer\n"
                "  - Step-by-step process or logic\n"
                "  - Examples or practical applications\n\n"
                "**Additional Notes:**\n"
                "  - Related insights, limitations, or context gaps\n\n"
                "**Source Reference:**\n"
                "  - Mention which document(s) or phrase(s) support your answer"
            )

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