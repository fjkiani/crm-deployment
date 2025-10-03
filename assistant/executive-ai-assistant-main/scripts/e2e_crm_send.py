import asyncio
import os
from eaia.crm_bridge import post_draft_with_provider, get_communication_for_ids, send_communication


async def main():
    # minimal e2e: create draft in CRM and optionally send
    email = {
        "from_email": os.getenv("EAIA_TEST_FROM", "sender@example.com"),
        "to_email": os.getenv("EAIA_TEST_TO", "me@example.com"),
        "subject": os.getenv("EAIA_TEST_SUBJECT", "EAIA E2E Test"),
        "page_content": "<p>Test body</p>",
        "id": os.getenv("EAIA_TEST_MESSAGE_ID", "test-mid-123"),
        "thread_id": os.getenv("EAIA_TEST_THREAD_ID", "test-tid-abc"),
        "html": "<p>Approved draft from EAIA</p>",
    }
    print("Posting draft...")
    resp = await post_draft_with_provider(email)
    print("Draft response:", resp)
    comm = get_communication_for_ids(email["id"], email["thread_id"]) or ""
    if os.getenv("EAIA_TEST_SEND", "0") == "1" and comm:
        print("Sending communication:", comm)
        send_resp = await send_communication(comm)
        print("Send response:", send_resp)


if __name__ == "__main__":
    asyncio.run(main())



