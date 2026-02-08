"""
Reply Matrix: The Fast Classifier
Classifies inbound email sentiment using heuristic keyword matching.
"""
import logging

logger = logging.getLogger(__name__)

class ReplyMatrix:
    """
    Classifies email content into actionable buckets.
    Buckets:
    - INTERESTED: Leads wants to talk.
    - NOT_INTERESTED: Lead says no.
    - UNSUBSCRIBE: Lead wants out (Compliance).
    - OOO: Auto-reply.
    - QUESTION: Needs human answer.
    """
    
    PATTERNS = {
        "INTERESTED": [
            "interested", "meet", "meeting", "call", "schedule", "calendar", 
            "talk", "chat", "available", "tuesday", "wednesday", "thursday", "friday",
            "sounds good", "send more info"
        ],
        "NOT_INTERESTED": [
            "not interested", "no thanks", "pass", "remove", "stop", 
            "spam", "don't email", "unsubscribe", "take me off"
        ],
        "Unsubscribe": [ # Specialized sub-category of Not Interested for Compliance
            "unsubscribe", "remove list", "stop emailing", "cease"
        ],
        "OOO": [
            "out of office", "automatic reply", "vacation", "on leave", 
            "limited access", "returning"
        ]
    }
    
    @staticmethod
    def classify(content: str) -> str:
        content = content.lower()
        
        # 1. OOO Check (Highest Priority to avoid noise)
        for w in ReplyMatrix.PATTERNS["OOO"]:
            if w in content:
                return "OOO"
                
        # 2. Unsubscribe / Compliance
        for w in ReplyMatrix.PATTERNS["Unsubscribe"]:
            if w in content:
                return "UNSUBSCRIBE"
                
        # 3. Not Interested
        for w in ReplyMatrix.PATTERNS["NOT_INTERESTED"]:
            if w in content:
                return "NOT_INTERESTED"
                
        # 4. Interested
        for w in ReplyMatrix.PATTERNS["INTERESTED"]:
            if w in content:
                return "INTERESTED"
                
        # 5. Fallback
        return "UNKNOWN"
