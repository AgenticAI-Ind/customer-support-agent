"""
Intelligent ticket routing with AI classification
"""

import logging
from typing import Dict, List, Optional
from enum import Enum
from langchain.prompts import PromptTemplate
from langchain_community.llms import Ollama

logger = logging.getLogger(__name__)


class TicketPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TicketCategory(str, Enum):
    TECHNICAL = "technical"
    BILLING = "billing"
    ACCOUNT = "account"
    PRODUCT = "product"
    GENERAL = "general"
    BUG = "bug"
    FEATURE_REQUEST = "feature_request"


class TicketRouter:
    """Intelligent ticket routing and classification"""

    def __init__(self, model_name: str = "llama3.2"):
        """Initialize ticket router"""
        self.llm = Ollama(model=model_name)

        self.routing_prompt = PromptTemplate(
            input_variables=["subject", "description", "customer_tier"],
            template="""You are an intelligent ticket routing system. Analyze this support ticket and provide routing information.

Ticket Details:
Subject: {subject}
Description: {description}
Customer Tier: {customer_tier}

Analyze and provide:
1. Category (technical, billing, account, product, general, bug, feature_request)
2. Priority (critical, high, medium, low)
3. Department (engineering, support, sales, billing, product)
4. Urgency Score (1-10)
5. Suggested Assignee Type (senior engineer, support specialist, billing expert, etc.)
6. Estimated Resolution Time (in hours)
7. Brief Reasoning

Respond in this exact format:
CATEGORY: [category]
PRIORITY: [priority]
DEPARTMENT: [department]
URGENCY: [1-10]
ASSIGNEE: [assignee type]
ETA: [hours]
REASONING: [brief explanation]
"""
        )

    def route_ticket(
        self,
        subject: str,
        description: str,
        customer_tier: str = "standard",
        customer_history: Optional[Dict] = None
    ) -> Dict:
        """
        Route a support ticket intelligently

        Args:
            subject: Ticket subject
            description: Ticket description
            customer_tier: Customer tier (free, standard, premium, enterprise)
            customer_history: Optional customer history data

        Returns:
            Dict with routing information
        """
        try:
            # Adjust priority based on customer tier
            tier_weight = {
                "enterprise": 2.0,
                "premium": 1.5,
                "standard": 1.0,
                "free": 0.5
            }.get(customer_tier.lower(), 1.0)

            # Generate routing recommendation
            prompt = self.routing_prompt.format(
                subject=subject,
                description=description[:1000],  # Limit description
                customer_tier=customer_tier
            )

            response = self.llm.invoke(prompt)

            # Parse response
            routing = self._parse_routing_response(response)

            # Apply customer tier adjustment
            routing['tier_weight'] = tier_weight
            routing['customer_tier'] = customer_tier

            # Consider customer history
            if customer_history:
                routing = self._adjust_for_history(routing, customer_history)

            logger.info(f"Routed ticket: {routing['category']}/{routing['priority']}")

            return routing

        except Exception as e:
            logger.error(f"Error routing ticket: {e}")
            return {
                "category": TicketCategory.GENERAL,
                "priority": TicketPriority.MEDIUM,
                "department": "support",
                "urgency": 5,
                "error": str(e)
            }

    def _parse_routing_response(self, response: str) -> Dict:
        """Parse LLM routing response"""
        routing = {
            "category": TicketCategory.GENERAL,
            "priority": TicketPriority.MEDIUM,
            "department": "support",
            "urgency": 5,
            "assignee_type": "support specialist",
            "eta_hours": 24,
            "reasoning": ""
        }

        for line in response.strip().split('\n'):
            if ':' not in line:
                continue

            key, value = line.split(':', 1)
            key = key.strip().lower()
            value = value.strip()

            if key == 'category':
                routing['category'] = value.lower()
            elif key == 'priority':
                routing['priority'] = value.lower()
            elif key == 'department':
                routing['department'] = value.lower()
            elif key == 'urgency':
                try:
                    routing['urgency'] = int(value)
                except:
                    routing['urgency'] = 5
            elif key == 'assignee':
                routing['assignee_type'] = value
            elif key == 'eta':
                try:
                    routing['eta_hours'] = float(value)
                except:
                    routing['eta_hours'] = 24
            elif key == 'reasoning':
                routing['reasoning'] = value

        return routing

    def _adjust_for_history(self, routing: Dict, history: Dict) -> Dict:
        """Adjust routing based on customer history"""
        # If customer has many open tickets, escalate
        open_tickets = history.get('open_tickets', 0)
        if open_tickets > 3:
            if routing['priority'] == TicketPriority.MEDIUM:
                routing['priority'] = TicketPriority.HIGH
            routing['urgency'] = min(10, routing['urgency'] + 2)

        # If customer has history of escalations, increase priority
        escalations = history.get('escalation_count', 0)
        if escalations > 0:
            routing['urgency'] = min(10, routing['urgency'] + 1)

        # If VIP customer, always high priority
        if history.get('is_vip', False):
            routing['priority'] = TicketPriority.HIGH
            routing['urgency'] = max(8, routing['urgency'])

        return routing

    def detect_duplicate_tickets(
        self,
        new_ticket: Dict,
        existing_tickets: List[Dict],
        similarity_threshold: float = 0.7
    ) -> List[Dict]:
        """
        Detect potential duplicate tickets

        Args:
            new_ticket: New ticket with subject and description
            existing_tickets: List of existing tickets
            similarity_threshold: Similarity threshold (0-1)

        Returns:
            List of similar tickets
        """
        try:
            from difflib import SequenceMatcher

            similar_tickets = []
            new_text = f"{new_ticket['subject']} {new_ticket['description']}".lower()

            for ticket in existing_tickets:
                existing_text = f"{ticket.get('subject', '')} {ticket.get('description', '')}".lower()

                similarity = SequenceMatcher(None, new_text, existing_text).ratio()

                if similarity >= similarity_threshold:
                    similar_tickets.append({
                        "ticket_id": ticket.get('id'),
                        "similarity": similarity,
                        "subject": ticket.get('subject'),
                        "status": ticket.get('status')
                    })

            return sorted(similar_tickets, key=lambda x: x['similarity'], reverse=True)

        except Exception as e:
            logger.error(f"Error detecting duplicates: {e}")
            return []

    def suggest_sla(self, routing: Dict) -> Dict:
        """
        Suggest SLA (Service Level Agreement) based on routing

        Args:
            routing: Routing information

        Returns:
            Dict with SLA targets
        """
        priority = routing.get('priority', TicketPriority.MEDIUM)
        customer_tier = routing.get('customer_tier', 'standard')

        # Base SLA targets (in hours)
        sla_targets = {
            TicketPriority.CRITICAL: {
                "first_response": 1,
                "resolution": 4
            },
            TicketPriority.HIGH: {
                "first_response": 4,
                "resolution": 24
            },
            TicketPriority.MEDIUM: {
                "first_response": 12,
                "resolution": 48
            },
            TicketPriority.LOW: {
                "first_response": 24,
                "resolution": 72
            }
        }

        sla = sla_targets.get(priority, sla_targets[TicketPriority.MEDIUM])

        # Adjust for customer tier
        if customer_tier == "enterprise":
            sla['first_response'] = max(0.5, sla['first_response'] * 0.5)
            sla['resolution'] = max(2, sla['resolution'] * 0.5)
        elif customer_tier == "premium":
            sla['first_response'] = max(1, sla['first_response'] * 0.75)
            sla['resolution'] = max(4, sla['resolution'] * 0.75)

        return {
            "first_response_hours": sla['first_response'],
            "resolution_hours": sla['resolution'],
            "priority": priority,
            "customer_tier": customer_tier
        }

    def batch_route(self, tickets: List[Dict]) -> List[Dict]:
        """
        Route multiple tickets in batch

        Args:
            tickets: List of ticket dicts with subject, description

        Returns:
            List of routing results
        """
        results = []
        for ticket in tickets:
            routing = self.route_ticket(
                subject=ticket.get('subject', ''),
                description=ticket.get('description', ''),
                customer_tier=ticket.get('customer_tier', 'standard'),
                customer_history=ticket.get('history')
            )
            routing['ticket_id'] = ticket.get('id')
            results.append(routing)

        return results

    def get_routing_stats(self, routed_tickets: List[Dict]) -> Dict:
        """Get statistics on routed tickets"""
        total = len(routed_tickets)
        if total == 0:
            return {}

        stats = {
            "total": total,
            "by_category": {},
            "by_priority": {},
            "by_department": {},
            "avg_urgency": 0,
            "avg_eta": 0
        }

        urgency_sum = 0
        eta_sum = 0

        for ticket in routed_tickets:
            # Category stats
            category = ticket.get('category', 'general')
            stats['by_category'][category] = stats['by_category'].get(category, 0) + 1

            # Priority stats
            priority = ticket.get('priority', 'medium')
            stats['by_priority'][priority] = stats['by_priority'].get(priority, 0) + 1

            # Department stats
            department = ticket.get('department', 'support')
            stats['by_department'][department] = stats['by_department'].get(department, 0) + 1

            # Averages
            urgency_sum += ticket.get('urgency', 5)
            eta_sum += ticket.get('eta_hours', 24)

        stats['avg_urgency'] = round(urgency_sum / total, 2)
        stats['avg_eta'] = round(eta_sum / total, 2)

        return stats
