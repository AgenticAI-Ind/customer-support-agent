"""
Automated response suggestions and resolution
"""

import logging
from typing import Dict, List, Optional
from langchain.prompts import PromptTemplate
from langchain_community.llms import Ollama

logger = logging.getLogger(__name__)


class AutoResponder:
    """Automated response generation and resolution suggestions"""

    def __init__(self, model_name: str = "llama3.2"):
        """Initialize auto responder"""
        self.llm = Ollama(model=model_name)

        self.resolution_prompt = PromptTemplate(
            input_variables=["issue_description", "category", "context"],
            template="""You are an expert customer support analyst. Analyze this support issue and suggest resolution steps.

Issue Category: {category}
Issue Description: {issue_description}
Additional Context: {context}

Provide:
1. Problem Summary (1 sentence)
2. Step-by-step Resolution (3-5 clear steps)
3. Estimated Resolution Time
4. Whether it requires human intervention (yes/no)

Format your response as:
SUMMARY: [one sentence]
STEPS:
1. [First step]
2. [Second step]
3. [Third step]
TIME: [estimated time]
NEEDS_HUMAN: [yes/no]
"""
        )

    def suggest_resolution(
        self,
        issue_description: str,
        category: str = "general",
        context: Optional[Dict] = None
    ) -> Dict:
        """
        Suggest resolution steps for an issue

        Args:
            issue_description: Description of the issue
            category: Issue category
            context: Additional context

        Returns:
            Dict with resolution suggestions
        """
        try:
            context_str = self._format_context(context)

            prompt = self.resolution_prompt.format(
                issue_description=issue_description[:1000],
                category=category,
                context=context_str
            )

            response = self.llm.invoke(prompt)

            # Parse response
            resolution = self._parse_resolution(response)

            logger.info(f"Generated resolution suggestion for {category} issue")

            return resolution

        except Exception as e:
            logger.error(f"Error suggesting resolution: {e}")
            return {
                "summary": "Error generating resolution",
                "steps": [],
                "error": str(e)
            }

    def _format_context(self, context: Optional[Dict]) -> str:
        """Format context information"""
        if not context:
            return "No additional context"

        parts = []
        if context.get('product'):
            parts.append(f"Product: {context['product']}")
        if context.get('customer_tier'):
            parts.append(f"Customer Tier: {context['customer_tier']}")
        if context.get('previous_attempts'):
            parts.append(f"Previous Attempts: {context['previous_attempts']}")

        return "; ".join(parts) if parts else "No additional context"

    def _parse_resolution(self, response: str) -> Dict:
        """Parse resolution response"""
        resolution = {
            "summary": "",
            "steps": [],
            "estimated_time": "Unknown",
            "needs_human": False
        }

        lines = response.strip().split('\n')
        current_section = None

        for line in lines:
            line = line.strip()

            if line.startswith('SUMMARY:'):
                resolution['summary'] = line.split(':', 1)[1].strip()
            elif line.startswith('STEPS:'):
                current_section = 'steps'
            elif line.startswith('TIME:'):
                resolution['estimated_time'] = line.split(':', 1)[1].strip()
            elif line.startswith('NEEDS_HUMAN:'):
                value = line.split(':', 1)[1].strip().lower()
                resolution['needs_human'] = value in ['yes', 'true']
            elif current_section == 'steps' and line:
                # Remove numbering
                step = line.lstrip('0123456789.-) ').strip()
                if step:
                    resolution['steps'].append(step)

        return resolution

    def generate_auto_response(
        self,
        ticket: Dict,
        resolution: Dict,
        tone: str = "professional"
    ) -> str:
        """
        Generate an automated response message

        Args:
            ticket: Ticket information
            resolution: Resolution suggestion
            tone: Response tone

        Returns:
            Generated response text
        """
        try:
            prompt = f"""Generate a {tone} customer support response for this issue:

Issue: {ticket.get('description', '')}
Resolution Steps: {'; '.join(resolution.get('steps', []))}

Write a helpful response that:
- Acknowledges the issue
- Provides clear steps to resolve it
- Is {tone} in tone
- Includes a closing offer to help further

Response:"""

            response = self.llm.invoke(prompt)

            return response.strip()

        except Exception as e:
            logger.error(f"Error generating auto response: {e}")
            return "Thank you for contacting support. We're looking into your issue and will get back to you shortly."

    def detect_common_issues(self, description: str) -> List[Dict]:
        """
        Detect if issue matches common known problems

        Args:
            description: Issue description

        Returns:
            List of matching common issues
        """
        # Common issue patterns (would be loaded from database in production)
        common_issues = [
            {
                "id": "login_failed",
                "keywords": ["can't login", "login failed", "password", "sign in"],
                "title": "Login Issues",
                "quick_fix": "Try resetting your password using the 'Forgot Password' link"
            },
            {
                "id": "payment_declined",
                "keywords": ["payment declined", "card declined", "payment failed"],
                "title": "Payment Declined",
                "quick_fix": "Check your card details and try again, or use a different payment method"
            },
            {
                "id": "slow_performance",
                "keywords": ["slow", "lagging", "loading", "performance"],
                "title": "Slow Performance",
                "quick_fix": "Clear your browser cache and cookies, or try a different browser"
            },
            {
                "id": "404_error",
                "keywords": ["404", "page not found", "broken link"],
                "title": "Page Not Found",
                "quick_fix": "Check the URL for typos or return to the homepage"
            }
        ]

        description_lower = description.lower()
        matches = []

        for issue in common_issues:
            if any(keyword in description_lower for keyword in issue['keywords']):
                matches.append(issue)

        return matches

    def generate_faq_response(self, question: str, faq_database: List[Dict]) -> Optional[Dict]:
        """
        Check if question matches FAQ

        Args:
            question: Customer question
            faq_database: List of FAQ entries

        Returns:
            Matching FAQ entry or None
        """
        question_lower = question.lower()

        for faq in faq_database:
            faq_question = faq.get('question', '').lower()
            keywords = faq.get('keywords', [])

            # Check for direct match or keyword match
            if faq_question in question_lower or any(k.lower() in question_lower for k in keywords):
                return {
                    "question": faq.get('question'),
                    "answer": faq.get('answer'),
                    "category": faq.get('category'),
                    "confidence": 0.9
                }

        return None

    def suggest_related_tickets(
        self,
        ticket: Dict,
        historical_tickets: List[Dict]
    ) -> List[Dict]:
        """
        Find related historical tickets

        Args:
            ticket: Current ticket
            historical_tickets: List of past tickets

        Returns:
            List of related tickets
        """
        from difflib import SequenceMatcher

        current_text = f"{ticket.get('subject', '')} {ticket.get('description', '')}".lower()
        related = []

        for hist_ticket in historical_tickets:
            hist_text = f"{hist_ticket.get('subject', '')} {hist_ticket.get('description', '')}".lower()

            similarity = SequenceMatcher(None, current_text, hist_text).ratio()

            if similarity > 0.6:
                related.append({
                    "ticket_id": hist_ticket.get('id'),
                    "similarity": similarity,
                    "subject": hist_ticket.get('subject'),
                    "resolution": hist_ticket.get('resolution'),
                    "resolution_time": hist_ticket.get('resolution_time')
                })

        return sorted(related, key=lambda x: x['similarity'], reverse=True)[:5]

    def estimate_resolution_time(
        self,
        category: str,
        priority: str,
        complexity: str = "medium"
    ) -> Dict:
        """
        Estimate resolution time based on ticket attributes

        Args:
            category: Ticket category
            priority: Ticket priority
            complexity: Issue complexity (low, medium, high)

        Returns:
            Dict with time estimates
        """
        # Base times in hours
        base_times = {
            "technical": 4,
            "billing": 2,
            "account": 1,
            "product": 3,
            "general": 2
        }

        base_time = base_times.get(category, 2)

        # Adjust for priority
        priority_multipliers = {
            "critical": 0.25,
            "high": 0.5,
            "medium": 1.0,
            "low": 1.5
        }

        priority_mult = priority_multipliers.get(priority, 1.0)

        # Adjust for complexity
        complexity_multipliers = {
            "low": 0.5,
            "medium": 1.0,
            "high": 2.0
        }

        complexity_mult = complexity_multipliers.get(complexity, 1.0)

        estimated_hours = base_time * priority_mult * complexity_mult

        return {
            "estimated_hours": round(estimated_hours, 1),
            "min_hours": round(estimated_hours * 0.7, 1),
            "max_hours": round(estimated_hours * 1.3, 1),
            "confidence": "medium"
        }
