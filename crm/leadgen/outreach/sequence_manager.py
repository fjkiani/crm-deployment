import frappe
from frappe.utils import now_datetime, add_days, get_datetime
from frappe import _
import json
from datetime import timedelta

def process_sequence_step(instance_name: str, step_number: int):
    """Process a single step in an outreach sequence"""
    try:
        instance = frappe.get_doc("Outreach Sequence Instance", instance_name)
        sequence = frappe.get_doc("Outreach Sequence", instance.outreach_sequence)
        prospect = frappe.get_doc("Lead Prospect", instance.lead_prospect)
        
        # Get the step configuration
        if step_number > len(sequence.steps):
            frappe.logger("sequence_manager").info(f"Step {step_number} not found in sequence {sequence.name}")
            return
        
        step = sequence.steps[step_number - 1]  # Steps are 1-indexed
        
        # Check if prospect has unsubscribed or bounced
        if instance.status in ["Unsubscribed", "Bounced"]:
            frappe.logger("sequence_manager").info(f"Prospect {prospect.name} has status {instance.status}, skipping step")
            return
        
        # Send the email
        email_sent = send_sequence_email(instance, prospect, step)
        
        if email_sent:
            # Update instance
            instance.current_step = step_number
            instance.last_contact_date = now_datetime()
            
            # Calculate next contact date
            if step_number < len(sequence.steps):
                next_step = sequence.steps[step_number]
                delay_days = next_step.get("delay_days", 3)
                instance.next_contact_date = add_days(now_datetime(), delay_days)
            else:
                # Sequence completed
                instance.status = "Completed"
                instance.next_contact_date = None
            
            instance.save(ignore_permissions=True)
            
            frappe.logger("sequence_manager").info(f"Sent step {step_number} for prospect {prospect.name}")
        else:
            frappe.logger("sequence_manager").error(f"Failed to send step {step_number} for prospect {prospect.name}")
            
    except Exception as e:
        frappe.log_error(f"Error processing sequence step {step_number} for instance {instance_name}: {str(e)}")

def send_sequence_email(instance, prospect, step):
    """Send an email for a sequence step"""
    try:
        # Generate personalized email content
        email_content = generate_personalized_email(prospect, step)
        
        # Send email using existing CRM email system
        email_doc = frappe.get_doc({
            "doctype": "Email",
            "recipients": prospect.pi_email,
            "subject": email_content["subject"],
            "content": email_content["body"],
            "reference_doctype": "Lead Prospect",
            "reference_name": prospect.name,
            "sender": step.get("sender_email") or instance.outreach_sequence.default_sender_email,
            "sender_name": step.get("sender_name") or instance.outreach_sequence.default_sender_name
        })
        
        email_doc.insert(ignore_permissions=True)
        email_doc.send()
        
        # Log the email in the instance
        log_email_send(instance, email_doc.name, step)
        
        return True
        
    except Exception as e:
        frappe.log_error(f"Error sending sequence email: {str(e)}")
        return False

def generate_personalized_email(prospect, step):
    """Generate personalized email content for a prospect"""
    # Get template content
    template_content = step.get("email_template", "")
    
    # Personalization variables
    personalization = {
        "pi_name": prospect.pi_name.split(" ")[0] if prospect.pi_name else "Dr.",
        "full_name": prospect.pi_name or "Dr.",
        "institution": prospect.institution or "your institution",
        "cancer_type": prospect.cancer_type or "oncology research",
        "tier": prospect.tier or "high-priority"
    }
    
    # Replace placeholders in template
    personalized_content = template_content
    for key, value in personalization.items():
        placeholder = f"{{{{{key}}}}}"
        personalized_content = personalized_content.replace(placeholder, str(value))
    
    # Generate subject line
    subject_template = step.get("subject_template", "Partnership Opportunity - {cancer_type}")
    subject = subject_template.format(**personalization)
    
    # Add unsubscribe link
    unsubscribe_link = f"<br><br><a href='{frappe.utils.get_url()}/api/method/crm.api.leadgen.unsubscribe?prospect={prospect.name}'>Unsubscribe</a>"
    personalized_content += unsubscribe_link
    
    return {
        "subject": subject,
        "body": personalized_content
    }

def log_email_send(instance, email_name, step):
    """Log email send in the sequence instance"""
    # Create email log entry
    email_log = frappe.get_doc({
        "doctype": "Outreach Email Log",
        "parent": instance.name,
        "parenttype": "Outreach Sequence Instance",
        "parentfield": "sent_emails",
        "email_name": email_name,
        "step_number": step.get("step_number", 1),
        "sent_at": now_datetime(),
        "status": "Sent"
    })
    email_log.insert(ignore_permissions=True)

def send_scheduled_follow_ups():
    """Send scheduled follow-up emails for active outreach sequences"""
    try:
        # Get instances ready for next contact
        ready_instances = frappe.get_all(
            "Outreach Sequence Instance",
            filters={
                "status": "Active",
                "next_contact_date": ["<=", now_datetime()]
            },
            fields=["name", "lead_prospect", "outreach_sequence", "current_step"]
        )
        
        frappe.logger("sequence_manager").info(f"Found {len(ready_instances)} instances ready for follow-up")
        
        for instance_data in ready_instances:
            try:
                # Process the next step
                next_step = instance_data.current_step + 1
                frappe.enqueue(
                    "crm.leadgen.outreach.sequence_manager.process_sequence_step",
                    instance_name=instance_data.name,
                    step_number=next_step,
                    queue="short"
                )
            except Exception as e:
                frappe.log_error(f"Error processing follow-up for instance {instance_data.name}: {str(e)}")
        
        frappe.logger("sequence_manager").info(f"Enqueued {len(ready_instances)} follow-up emails")
        
    except Exception as e:
        frappe.log_error(f"Error in send_scheduled_follow_ups: {str(e)}")

def create_default_outreach_sequences():
    """Create default outreach sequences for different tiers"""
    sequences = [
        {
            "title": "Tier 1 - High Priority Outreach",
            "description": "Comprehensive outreach sequence for Tier 1 prospects",
            "steps": [
                {
                    "step_number": 1,
                    "delay_days": 0,
                    "subject_template": "Partnership Opportunity - {cancer_type} Research",
                    "email_template": get_tier1_initial_template(),
                    "sender_name": "Dr. Sarah Johnson",
                    "sender_email": "sarah.johnson@company.com"
                },
                {
                    "step_number": 2,
                    "delay_days": 3,
                    "subject_template": "Follow-up: Genomic Stratification Partnership",
                    "email_template": get_tier1_followup_template(),
                    "sender_name": "Dr. Sarah Johnson",
                    "sender_email": "sarah.johnson@company.com"
                },
                {
                    "step_number": 3,
                    "delay_days": 7,
                    "subject_template": "Final Follow-up: Clinical Trial Partnership",
                    "email_template": get_tier1_final_template(),
                    "sender_name": "Dr. Sarah Johnson",
                    "sender_email": "sarah.johnson@company.com"
                }
            ]
        },
        {
            "title": "Tier 2 - Standard Outreach",
            "description": "Standard outreach sequence for Tier 2 prospects",
            "steps": [
                {
                    "step_number": 1,
                    "delay_days": 0,
                    "subject_template": "Oncology Research Partnership Opportunity",
                    "email_template": get_tier2_initial_template(),
                    "sender_name": "Dr. Michael Chen",
                    "sender_email": "michael.chen@company.com"
                },
                {
                    "step_number": 2,
                    "delay_days": 5,
                    "subject_template": "Follow-up: Genomic Stratification",
                    "email_template": get_tier2_followup_template(),
                    "sender_name": "Dr. Michael Chen",
                    "sender_email": "michael.chen@company.com"
                }
            ]
        },
        {
            "title": "Tier 3 - Basic Outreach",
            "description": "Basic outreach sequence for Tier 3 prospects",
            "steps": [
                {
                    "step_number": 1,
                    "delay_days": 0,
                    "subject_template": "Clinical Trial Partnership Inquiry",
                    "email_template": get_tier3_template(),
                    "sender_name": "Dr. Emily Rodriguez",
                    "sender_email": "emily.rodriguez@company.com"
                }
            ]
        }
    ]
    
    for seq_data in sequences:
        # Check if sequence already exists
        existing = frappe.get_all("Outreach Sequence", filters={"title": seq_data["title"]}, limit=1)
        if existing:
            continue
        
        # Create sequence
        sequence = frappe.get_doc({
            "doctype": "Outreach Sequence",
            "title": seq_data["title"],
            "description": seq_data["description"],
            "status": "Active",
            "default_sender_name": seq_data["steps"][0]["sender_name"],
            "default_sender_email": seq_data["steps"][0]["sender_email"]
        })
        
        # Add steps
        for step_data in seq_data["steps"]:
            step_doc = frappe.get_doc({
                "doctype": "Outreach Sequence Step",
                "parent": sequence.name,
                "parenttype": "Outreach Sequence",
                "parentfield": "steps",
                "step_number": step_data["step_number"],
                "delay_days": step_data["delay_days"],
                "subject_template": step_data["subject_template"],
                "email_template": step_data["email_template"],
                "sender_name": step_data["sender_name"],
                "sender_email": step_data["sender_email"]
            })
            sequence.append("steps", step_doc)
        
        sequence.insert(ignore_permissions=True)
        frappe.logger("sequence_manager").info(f"Created outreach sequence: {seq_data['title']}")

def get_tier1_initial_template():
    """Get Tier 1 initial email template"""
    return """
Dear {pi_name},

I hope this email finds you well. I'm reaching out regarding your {cancer_type} research at {institution}.

Our company specializes in genomic patient stratification for oncology clinical trials, and we've been following your work with great interest. Given your expertise in {cancer_type}, I believe there's a significant opportunity for collaboration.

We're currently working with leading oncology centers to improve clinical trial success rates through precision medicine approaches. Our genomic stratification platform has shown promising results in identifying patients most likely to respond to specific treatments.

Would you be available for a brief 15-minute call this week to discuss how we might support your current or upcoming clinical trials? I'd be happy to share more details about our platform and explore potential partnership opportunities.

I've attached a brief overview of our technology and recent case studies that might be of interest.

Looking forward to hearing from you.

Best regards,
Dr. Sarah Johnson
VP of Clinical Partnerships
Genomic Stratification Solutions

P.S. If you're not the right person to discuss clinical trial partnerships, I'd appreciate it if you could forward this to the appropriate colleague.
"""

def get_tier1_followup_template():
    """Get Tier 1 follow-up email template"""
    return """
Dear {pi_name},

I wanted to follow up on my previous email regarding potential collaboration on your {cancer_type} research.

I understand you're likely very busy with your clinical work, but I believe our genomic stratification platform could significantly benefit your current trials. We've helped similar institutions reduce trial failure rates by up to 40% through better patient selection.

A few key points about our approach:
- Non-invasive genomic profiling from standard blood samples
- Integration with existing trial protocols
- Proven ROI through improved patient outcomes
- Full regulatory compliance and RUO status

Would you have 10 minutes for a quick call this week? I can also arrange a brief demo of our platform if that would be helpful.

Thank you for your time and consideration.

Best regards,
Dr. Sarah Johnson
"""

def get_tier1_final_template():
    """Get Tier 1 final email template"""
    return """
Dear {pi_name},

This is my final follow-up regarding our genomic stratification partnership opportunity.

I understand you may not be interested at this time, but I wanted to leave you with one final thought: our platform is specifically designed to address the 60% failure rate in Phase 3 oncology trials through better patient stratification.

If you're interested in learning more in the future, please don't hesitate to reach out. We're always happy to discuss how precision medicine can improve clinical trial outcomes.

Thank you for your time and consideration.

Best regards,
Dr. Sarah Johnson

P.S. If you'd like to unsubscribe from future communications, please click here.
"""

def get_tier2_initial_template():
    """Get Tier 2 initial email template"""
    return """
Dear {pi_name},

I hope this email finds you well. I'm reaching out regarding your {cancer_type} research at {institution}.

Our company specializes in genomic patient stratification for oncology clinical trials. We're currently working with several leading oncology centers to improve trial success rates through precision medicine approaches.

Would you be interested in learning more about how our platform might support your clinical trials? I'd be happy to schedule a brief call to discuss potential collaboration opportunities.

Best regards,
Dr. Michael Chen
Clinical Partnerships Manager
Genomic Stratification Solutions
"""

def get_tier2_followup_template():
    """Get Tier 2 follow-up email template"""
    return """
Dear {pi_name},

I wanted to follow up on my previous email regarding our genomic stratification platform.

Our platform has helped oncology centers improve clinical trial outcomes through better patient selection. If you're interested in learning more, I'd be happy to arrange a brief call or demo.

Thank you for your time.

Best regards,
Dr. Michael Chen
"""

def get_tier3_template():
    """Get Tier 3 email template"""
    return """
Dear {pi_name},

I hope this email finds you well. I'm reaching out regarding your {cancer_type} research at {institution}.

Our company specializes in genomic patient stratification for oncology clinical trials. We're currently working with several leading oncology centers to improve trial success rates.

Would you be interested in learning more about our platform? I'd be happy to schedule a brief call to discuss potential collaboration opportunities.

Best regards,
Dr. Emily Rodriguez
Clinical Partnerships Associate
Genomic Stratification Solutions
"""


