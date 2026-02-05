import sys
import os
import json
from dotenv import load_dotenv

# 1. Setup Environment
# Point to the secrets file we know exists
secrets_path = "/Users/fahadkiani/Desktop/development/crm-develop/assistant/executive-ai-assistant-main/eaia/.secrets/.env"
load_dotenv(secrets_path)

# 2. Setup Python Path to include 'src'
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, "src")
sys.path.append(src_path)

print(f"⚔️  Verifying Farfalle Intel Engine...")
print(f"    Secret Path: {secrets_path}")
print(f"    TAVILY_KEY present: {bool(os.getenv('TAVILY_API_KEY'))}")
print(f"    DIFFBOT_TOKEN present: {bool(os.getenv('DIFFBOT_TOKEN'))}")
print(f"    LINKEDIN_KEY present: {bool(os.getenv('LINKEDIN_RAPIDAPI_KEY'))}")

try:
    from backend.intel.services import build_intel_service_from_env
except ImportError as e:
    print(f"❌ Import Failed: {e}")
    sys.exit(1)

def run_test():
    print("\n🔍 Running Analysis on 'BlackRock'...")
    service = build_intel_service_from_env()
    
    # Simulate the questions from router.py
    questions = [
        "Who are the decision-makers at BlackRock?",
        "What has BlackRock invested in recently in 2024?",
        "What is BlackRock's AUM?"
    ]
    
    try:
        # We assume domain is None for now to test raw search
        result = service.analyze(company="BlackRock", questions=questions, max_results=3)
        
        print("\n✅ Analysis Complete. Raw Results Summary:")
        print(f"   Total Sources Used: {result.get('total_sources')}")
        
        for item in result.get('results', []):
            q = item.get('question')
            ans = item.get('answer')
            sources = len(item.get('sources', []))
            print(f"   \n❓ Q: {q}")
            print(f"   💡 A: {ans[:150]}..." if ans else "   💡 A: [No direct answer]")
            print(f"      ({sources} sources)")

            # Check for "Stereoids" (Diffbot/LinkedIn extraction)
            people = item.get('extracted_people', [])
            if people:
                print(f"      🧑 Extracted People: {len(people)}")
                for p in people[:2]:
                    print(f"         - {p.get('name')} ({p.get('title')})")
            else:
                print(f"      🧑 Extracted People: None (Requires Diffbot/LinkedIn Keys)")

    except Exception as e:
        print(f"❌ Execution Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_test()
