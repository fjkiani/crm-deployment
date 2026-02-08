"""
Agent Zo2: "The Closer"
Mission: Handle inbound replies and close the loop.
"""
import logging
import os
import requests
from dotenv import load_dotenv
from eaia.skills.reply_matrix import ReplyMatrix

# Load secrets relative to this file
params_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".secrets", ".env"))
load_dotenv(params_path)

logger = logging.getLogger(__name__)

class CRMCloserClient:
    def __init__(self):
        self.base_url = os.getenv("FRAPPE_URL", "http://localhost:8000")
        self.api_key = os.getenv("FRAPPE_API_KEY")
        self.api_secret = os.getenv("FRAPPE_API_SECRET")
        self.headers = {
            "Authorization": f"token {self.api_key}:{self.api_secret}",
            "Content-Type": "application/json"
        }

    def update_lead_status(self, email: str, status: str, notes: str = None):
        """
        Updates Lead Prospect status based on reply.
        """
        if not self.api_key:
            logger.warning(f"Mocking CRM Close: {email} -> {status}")
            return
            
        try:
            # 1. Find Prospect by Email
            filters = f'[["pi_email","=","{email}"]]'
            search_url = f"{self.base_url}/api/resource/Lead Prospect?filters={filters}"
            resp = requests.get(search_url, headers=self.headers)
            data = resp.json().get("data", [])
            
            if not data:
                logger.warning(f"❌ Prospect not found for reply: {email}")
                return
                
            doc_name = data[0]["name"]
            
            # 2. Update Status
            update_data = {"outreach_status": status}
            if notes:
                update_data["notes"] = f"{data[0].get('notes','')}\n[Zo2]: {notes}"
                
            update_url = f"{self.base_url}/api/resource/Lead Prospect/{doc_name}"
            requests.put(update_url, headers=self.headers, json=update_data)
            logger.info(f"✅ Zo2 Closed Loop: {email} -> {status}")
            
        except Exception as e:
            logger.error(f"❌ CRM Close Error: {e}")

async def zo2_closer_agent(inbound_email: dict):
    """
    Async handler for inbound replies.
    Input: {"from": "me@example.com", "body": "Let's talk", "subject": "Re: Trial"}
    """
    sender = inbound_email.get("from")
    body = inbound_email.get("body", "")
    
    logger.info(f"📨 Zo2 Received Reply from: {sender}")
    
    # 1. Classify
    sentiment = ReplyMatrix.classify(body)
    logger.info(f"🧠 Zo2 Analysis: {sentiment}")
    
    client = CRMCloserClient()
    
    # 2. Act
    if sentiment == "INTERESTED":
        client.update_lead_status(sender, "Meeting Scheduled", f"Interested Reply: {body[:50]}...")
        # TODO: Trigger Alert to Human Slack/Email
        
    elif sentiment == "UNSUBSCRIBE":
        client.update_lead_status(sender, "Closed", "Unsubscribed via Reply")
        # TODO: Add to Global Blocklist
        
    elif sentiment == "OOO":
        logger.info("💤 Snoozing OOO reply.")
        # No status change, maybe log it
        
    elif sentiment == "NOT_INTERESTED":
        client.update_lead_status(sender, "Closed", "Not Interested")
        
    else:
        client.update_lead_status(sender, "Replied", f"Unclassified Reply: {body[:50]}...")
        
    return {"status": "HANDLED", "sentiment": sentiment}
