"""
Template Engine
Manages email templates and personalization rules
"""

from typing import Dict, List, Any, Optional
import json
from pathlib import Path
from string import Template

class TemplateEngine:
    """Manages email templates and personalization"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.templates = {}
        self.personalization_rules = {}

        self._load_templates()
        self._load_personalization_rules()

    def _load_templates(self):
        """Load email templates"""
        # Default templates based on our 3EDGE success
        self.templates = {
            "executive_outreach": {
                "subject": "AI-Powered Intelligence: Solving ${company}'s Strategic Challenges",
                "body": """Dear ${contact_name},

As ${title} at ${company}, you're navigating complex challenges in today's market.

Our AI-powered solutions directly address your key challenges:
• ${pain_point_1}
• ${pain_point_2}
• ${pain_point_3}

Would you be available for a brief conversation?

Best regards,
${sender_name}
${sender_title}
${sender_company}""",
                "ps": "P.S. I'd love to discuss how AI can support ${company}'s growth."
            },

            "president_outreach": {
                "subject": "Scaling ${company}: AI-Driven Growth Solutions",
                "body": """Dear ${contact_name},

Congratulations on your leadership role at ${company}.

Our AI solutions help Presidents like you:
• Scale client acquisition efficiently
• Automate operational workflows
• Drive business growth through data-driven insights

Let's explore how we're helping similar organizations.

Best regards,
${sender_name}""",
                "ps": "P.S. Your recent team expansion shows strong growth trajectory."
            }
        }

    def _load_personalization_rules(self):
        """Load personalization rules based on our 3EDGE analysis"""
        self.personalization_rules = {
            "CEO": {
                "pain_points": ["Portfolio optimization", "Market prediction", "Risk management"],
                "communication_style": "Strategic, ROI-focused",
                "template": "executive_outreach"
            },
            "President": {
                "pain_points": ["Client acquisition", "Operational scaling", "Business growth"],
                "communication_style": "Business-focused, growth-oriented",
                "template": "president_outreach"
            },
            "CIO": {
                "pain_points": ["Data analysis", "Technology integration", "Innovation"],
                "communication_style": "Technical, innovation-focused",
                "template": "executive_outreach"
            },
            "Director": {
                "pain_points": ["Team management", "Process optimization", "Strategic planning"],
                "communication_style": "Operational, implementation-focused",
                "template": "executive_outreach"
            }
        }

    def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get template by name"""
        return self.templates.get(template_name)

    def get_personalization_rules(self, role: str) -> Dict[str, Any]:
        """Get personalization rules for role"""
        return self.personalization_rules.get(role, self.personalization_rules.get("Director", {}))

    def render_template(self, template_name: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Render template with variables"""
        template = self.get_template(template_name)
        if not template:
            return {}

        rendered = {}
        for key, content in template.items():
            if isinstance(content, str):
                try:
                    rendered[key] = Template(content).safe_substitute(variables)
                except Exception as e:
                    rendered[key] = content  # Fallback to original
            else:
                rendered[key] = content

        return rendered

    def create_personalized_content(self, contact: Dict[str, Any], company_context: Dict[str, Any]) -> Dict[str, Any]:
        """Create personalized content based on our 3EDGE methodology"""
        role = contact.get('title', 'Director')
        rules = self.get_personalization_rules(role)

        # Prepare variables for template
        variables = {
            "contact_name": contact.get('name', 'Valued Contact').split()[0],
            "title": role,
            "company": company_context.get('company_name', 'your company'),
            "sender_name": self.config.get('sender_name', '[Your Name]'),
            "sender_title": self.config.get('sender_title', '[Your Title]'),
            "sender_company": self.config.get('sender_company', '[Your Company]'),
            "pain_point_1": rules['pain_points'][0],
            "pain_point_2": rules['pain_points'][1],
            "pain_point_3": rules['pain_points'][2]
        }

        # Render template
        template_name = rules.get('template', 'executive_outreach')
        rendered = self.render_template(template_name, variables)

        # Add personalization metadata
        rendered.update({
            "personalization_score": self._calculate_personalization_score(contact, company_context),
            "communication_style": rules['communication_style'],
            "target_pain_points": rules['pain_points']
        })

        return rendered

    def _calculate_personalization_score(self, contact: Dict[str, Any], company_context: Dict[str, Any]) -> float:
        """Calculate personalization effectiveness score"""
        score = 0.5  # Base score

        # Name personalization
        if contact.get('name') and len(contact['name'].split()) > 1:
            score += 0.2

        # Role-specific content
        if contact.get('title'):
            score += 0.15

        # Company-specific references
        if company_context.get('company_name'):
            score += 0.15

        # Pain point alignment
        if company_context.get('focus_areas'):
            score += 0.1

        return min(score, 1.0)
