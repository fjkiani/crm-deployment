"""
Test Script: The Feedback Loop (Phase 5)
Simulates inbound replies and verifies Zo2's response.
"""
import asyncio
import logging
from eaia.agents.zo2 import zo2_closer_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_feedback_simulation():
    print("\n📩 Simulating Inbound Replies...\n")
    
    # Scene 1: The Interested Lead
    email_1 = {
        "from": "melissa.johnson@scri.com",
        "subject": "Re: Partnership",
        "body": "Hi, I'm interested in discussing this further. Does next Tuesday work to meet?"
    }
    await zo2_closer_agent(email_1)
    
    # Scene 2: The Opt-Out
    email_2 = {
        "from": "krisann.schultz@childrensmn.org",
        "subject": "Stop",
        "body": "Please remove me from your list. Unsubscribe."
    }
    await zo2_closer_agent(email_2)
    
    # Scene 3: The OOO
    email_3 = {
        "from": "louise.acheson@case.edu",
        "subject": "Automatic Reply: Out of Office",
        "body": "I am out of the office until Feb 10th with limited access to email."
    }
    await zo2_closer_agent(email_3)

    print("\n✅ Simulation Complete. Check CRM logs or dashboard.")

if __name__ == "__main__":
    asyncio.run(run_feedback_simulation())
