"""
Multi-language AI chatbot for customer support
"""

import logging
from typing import Dict, List, Optional
from langchain.prompts import PromptTemplate
from langchain_community.llms import Ollama
from datetime import datetime

logger = logging.getLogger(__name__)


class SupportChatbot:
    """AI-powered customer support chatbot"""

    def __init__(self, model_name: str = "llama3.2"):
        """Initialize support chatbot"""
        self.llm = Ollama(model=model_name)
        self.conversations = {}  # Store conversation histories

        self.chat_prompt = PromptTemplate(
            input_variables=["conversation_history", "customer_message", "context"],
            template="""You are a helpful customer support assistant. Your goal is to help customers solve their problems professionally and empathetically.

Context about the customer:
{context}

Conversation History:
{conversation_history}

Customer: {customer_message}

Provide a helpful, professional, and empathetic response. If you need more information, ask clarifying questions. If the issue requires human intervention, suggest contacting an agent.

Response:"""
        )

    def chat(
        self,
        conversation_id: str,
        message: str,
        customer_context: Optional[Dict] = None,
        language: str = "en"
    ) -> Dict:
        """
        Process a customer message and generate response

        Args:
            conversation_id: Unique conversation identifier
            message: Customer's message
            customer_context: Optional customer information
            language: Language code (en, es, fr, etc.)

        Returns:
            Dict with response and metadata
        """
        try:
            # Get or create conversation history
            if conversation_id not in self.conversations:
                self.conversations[conversation_id] = {
                    "messages": [],
                    "started_at": datetime.now().isoformat(),
                    "language": language
                }

            conversation = self.conversations[conversation_id]

            # Build conversation history string
            history = self._format_history(conversation['messages'])

            # Build context
            context = self._build_context(customer_context)

            # Generate response
            prompt = self.chat_prompt.format(
                conversation_history=history,
                customer_message=message,
                context=context
            )

            response = self.llm.invoke(prompt)

            # Save to history
            conversation['messages'].append({
                "role": "customer",
                "content": message,
                "timestamp": datetime.now().isoformat()
            })

            conversation['messages'].append({
                "role": "assistant",
                "content": response.strip(),
                "timestamp": datetime.now().isoformat()
            })

            # Detect if escalation is needed
            needs_escalation = self._detect_escalation(message, response)

            logger.info(f"Chat response generated for conversation {conversation_id}")

            return {
                "response": response.strip(),
                "conversation_id": conversation_id,
                "needs_escalation": needs_escalation,
                "language": language,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return {
                "response": "I apologize, but I'm having trouble processing your request. Please try again or contact support.",
                "error": str(e),
                "conversation_id": conversation_id
            }

    def _format_history(self, messages: List[Dict]) -> str:
        """Format conversation history for prompt"""
        if not messages:
            return "No previous messages"

        history_lines = []
        for msg in messages[-10:]:  # Last 10 messages
            role = "Customer" if msg['role'] == "customer" else "Assistant"
            history_lines.append(f"{role}: {msg['content']}")

        return "\n".join(history_lines)

    def _build_context(self, customer_context: Optional[Dict]) -> str:
        """Build customer context string"""
        if not customer_context:
            return "No customer context available"

        context_parts = []

        if customer_context.get('name'):
            context_parts.append(f"Customer Name: {customer_context['name']}")

        if customer_context.get('account_type'):
            context_parts.append(f"Account Type: {customer_context['account_type']}")

        if customer_context.get('previous_issues'):
            context_parts.append(f"Previous Issues: {customer_context['previous_issues']}")

        if customer_context.get('product'):
            context_parts.append(f"Product: {customer_context['product']}")

        return "\n".join(context_parts) if context_parts else "No customer context available"

    def _detect_escalation(self, message: str, response: str) -> bool:
        """Detect if conversation needs escalation to human agent"""
        escalation_keywords = [
            "speak to a human",
            "talk to manager",
            "this is unacceptable",
            "cancel my account",
            "refund",
            "lawyer",
            "sue",
            "complaint"
        ]

        message_lower = message.lower()
        response_lower = response.lower()

        # Check customer message for escalation triggers
        if any(keyword in message_lower for keyword in escalation_keywords):
            return True

        # Check if bot suggested escalation
        if "contact" in response_lower and ("agent" in response_lower or "human" in response_lower):
            return True

        return False

    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Get conversation history"""
        return self.conversations.get(conversation_id)

    def get_conversation_summary(self, conversation_id: str) -> Dict:
        """
        Get a summary of the conversation

        Args:
            conversation_id: Conversation identifier

        Returns:
            Dict with summary information
        """
        conversation = self.conversations.get(conversation_id)

        if not conversation:
            return {"error": "Conversation not found"}

        messages = conversation['messages']

        return {
            "conversation_id": conversation_id,
            "message_count": len(messages),
            "started_at": conversation.get('started_at'),
            "language": conversation.get('language', 'en'),
            "customer_messages": len([m for m in messages if m['role'] == 'customer']),
            "assistant_messages": len([m for m in messages if m['role'] == 'assistant'])
        }

    def translate_message(
        self,
        message: str,
        source_lang: str,
        target_lang: str
    ) -> str:
        """
        Translate a message to another language

        Args:
            message: Message to translate
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            Translated message
        """
        try:
            prompt = f"""Translate this message from {source_lang} to {target_lang}. Maintain the tone and meaning.

Message: {message}

Translation:"""

            translation = self.llm.invoke(prompt)
            return translation.strip()

        except Exception as e:
            logger.error(f"Translation error: {e}")
            return message  # Return original on error

    def generate_canned_responses(self, category: str) -> List[str]:
        """
        Generate canned responses for common scenarios

        Args:
            category: Response category (greeting, closing, apology, etc.)

        Returns:
            List of canned responses
        """
        prompts = {
            "greeting": "Generate 5 professional greeting messages for customer support chat.",
            "closing": "Generate 5 professional closing messages for customer support chat.",
            "apology": "Generate 5 empathetic apology messages for customer support issues.",
            "acknowledgment": "Generate 5 acknowledgment messages showing we received customer feedback."
        }

        prompt = prompts.get(category, "Generate 5 helpful customer support messages.")

        try:
            response = self.llm.invoke(prompt)
            # Parse responses (assuming numbered list)
            responses = []
            for line in response.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-')):
                    # Remove numbering
                    clean_line = line.lstrip('0123456789.-) ').strip()
                    if clean_line:
                        responses.append(clean_line)

            return responses[:5]  # Return max 5

        except Exception as e:
            logger.error(f"Error generating canned responses: {e}")
            return []

    def suggest_next_action(self, conversation_id: str) -> Dict:
        """
        Suggest next action based on conversation

        Args:
            conversation_id: Conversation identifier

        Returns:
            Dict with suggested action
        """
        conversation = self.conversations.get(conversation_id)

        if not conversation:
            return {"action": "unknown", "reason": "Conversation not found"}

        messages = conversation['messages']

        if len(messages) == 0:
            return {"action": "start_conversation", "reason": "No messages yet"}

        # Get last few messages
        recent = messages[-4:]

        # Simple rule-based suggestions
        last_customer_msg = next((m['content'] for m in reversed(messages) if m['role'] == 'customer'), "")

        if self._detect_escalation(last_customer_msg, ""):
            return {
                "action": "escalate_to_human",
                "reason": "Customer requesting human assistance",
                "priority": "high"
            }

        if len(messages) > 20:
            return {
                "action": "summarize_and_close",
                "reason": "Long conversation, consider summarizing",
                "priority": "medium"
            }

        # Check for resolution
        resolution_keywords = ["thank you", "thanks", "solved", "fixed", "resolved", "perfect"]
        if any(keyword in last_customer_msg.lower() for keyword in resolution_keywords):
            return {
                "action": "confirm_resolution",
                "reason": "Customer seems satisfied",
                "priority": "low"
            }

        return {
            "action": "continue_conversation",
            "reason": "Ongoing support interaction",
            "priority": "normal"
        }

    def clear_conversation(self, conversation_id: str):
        """Clear conversation history"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            logger.info(f"Cleared conversation {conversation_id}")

    def get_active_conversations(self) -> List[str]:
        """Get list of active conversation IDs"""
        return list(self.conversations.keys())

    def export_conversation(self, conversation_id: str) -> Optional[Dict]:
        """
        Export conversation for analysis or archiving

        Args:
            conversation_id: Conversation identifier

        Returns:
            Dict with full conversation data
        """
        return self.conversations.get(conversation_id)
