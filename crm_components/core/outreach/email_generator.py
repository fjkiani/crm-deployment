"""
Email Generator Component
Creates personalized email content
"""

from core.component_base import OutreachComponent
from typing import Dict, List, Any

class EmailGeneratorComponent(OutreachComponent):
    """Generate personalized emails - 62 lines"""

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate personalized email"""
        recipient = input_data.get('recipient', {})
        intelligence = input_data.get('intelligence', {})

        # Generate email content
        email_content = self._generate_email(recipient, intelligence)

        # Calculate personalization score
        personalization_score = self._calculate_personalization_score(recipient, intelligence)

        result = {
            "recipient": recipient,
            "email": email_content,
            "personalization_score": personalization_score,
            "generated_at": self.created_at.isoformat()
        }

        self._execution_count = getattr(self, '_execution_count', 0) + 1
        return result

    def _generate_email(self, recipient: Dict[str, Any], intelligence: Dict[str, Any]) -> Dict[str, Any]:
        """Generate email content"""
        name = recipient.get('name', 'Valued Contact').split()[0]
        title = recipient.get('title', 'Professional')
        company = intelligence.get('company_name', 'your company')

        subject = self._generate_subject(title, company)
        body = self._generate_body(name, title, intelligence)
        ps = self._generate_ps(intelligence)

        return {
            "subject": subject,
            "body": body,
            "ps": ps,
            "from": self.sender_info.get('email', 'noreply@company.com'),
            "to": recipient.get('email', ''),
            "sender_name": self.sender_info.get('name', 'Your Company')
        }

    def _generate_subject(self, title: str, company: str) -> str:
        """Generate email subject"""
        if 'CEO' in title or 'Chief' in title:
            return f"AI-Powered Intelligence: Solving {company}'s Strategic Challenges"
        elif 'VP' in title or 'Director' in title:
            return f"Operational Excellence: How AI Can Transform {company}"
        else:
            return f"AI Innovation: Next-Gen Solutions for {company}"

    def _generate_body(self, name: str, title: str, intelligence: Dict[str, Any]) -> str:
        """Generate email body"""
        company = intelligence.get('company_name', 'your company')
        focus_areas = intelligence.get('focus_areas', [])

        body = f"""Dear {name},

As {title} at {company}, you're navigating complex challenges in today's market.

Our AI-powered solutions can help with:
• {focus_areas[0] if focus_areas else 'Advanced analytics'}
• {focus_areas[1] if len(focus_areas) > 1 else 'Process optimization'}
• {focus_areas[2] if len(focus_areas) > 2 else 'Strategic insights'}

Would you be available for a brief conversation?

Best regards,
{self.sender_info.get('name', 'Your Name')}
{self.sender_info.get('title', 'Your Title')}
{self.sender_info.get('company', 'Your Company')}"""

        return body

    def _generate_ps(self, intelligence: Dict[str, Any]) -> str:
        """Generate P.S."""
        company = intelligence.get('company_name', 'your company')
        return f"P.S. I'd love to discuss how AI can support {company}'s continued growth."

    def _calculate_personalization_score(self, recipient: Dict[str, Any], intelligence: Dict[str, Any]) -> float:
        """Calculate personalization effectiveness"""
        score = 0.0

        # Name usage
        if recipient.get('name') and len(recipient['name'].split()) > 1:
            score += 0.3

        # Title-specific content
        if recipient.get('title'):
            score += 0.2

        # Company-specific references
        if intelligence.get('company_name'):
            score += 0.3

        # Industry relevance
        if intelligence.get('focus_areas'):
            score += 0.2

        return min(score, 1.0)
