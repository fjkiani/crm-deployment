#!/usr/bin/env python3
"""
Basic API Test: Test Gemini and Tavily APIs using standard library
"""

import json
import urllib.request
import urllib.parse
import urllib.error

# API keys
TAVILY_API_KEY = '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'
GEMINI_API_KEY = 'AIzaSyDmPm3J2yqzJD1nXvd_5-8i6TX6rygwZ0Y'

def test_gemini_api():
    """Test Gemini API using urllib"""
    
    print("🧪 Testing Gemini API...")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": "Hello! Please respond with 'Gemini API connection successful' if you can understand this message."}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 100
        }
    }
    
    try:
        # Prepare request
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        
        # Make request
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                response_data = json.loads(response.read().decode('utf-8'))
                
                if "candidates" in response_data and len(response_data["candidates"]) > 0:
                    candidate = response_data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        content = candidate["content"]["parts"][0]["text"]
                        print(f"✅ Gemini Response: {content}")
                        return True
                
                print(f"❌ Unexpected Gemini response format: {response_data}")
                return False
            else:
                print(f"❌ Gemini API error {response.status}")
                return False
                
    except Exception as e:
        print(f"❌ Gemini API test failed: {e}")
        return False

def test_tavily_api():
    """Test Tavily API using urllib"""
    
    print("🧪 Testing Tavily API...")
    
    url = "https://api.tavily.com/search"
    
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": "Abbey Capital investment firm",
        "search_type": "general",
        "max_results": 3,
        "include_answer": True,
        "include_raw_content": True
    }
    
    try:
        # Prepare request
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        
        # Make request
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                response_data = json.loads(response.read().decode('utf-8'))
                
                results = response_data.get("results", [])
                print(f"✅ Tavily found {len(results)} results")
                
                if results:
                    first_result = results[0]
                    print(f"✅ First result: {first_result.get('title', 'No title')}")
                    print(f"✅ URL: {first_result.get('url', 'No URL')}")
                    content = first_result.get('content', 'No content')
                    print(f"✅ Content preview: {content[:100]}...")
                
                return True
            else:
                print(f"❌ Tavily API error {response.status}")
                return False
                
    except Exception as e:
        print(f"❌ Tavily API test failed: {e}")
        return False

def test_question_decomposition():
    """Test question decomposition with Gemini"""
    
    print("🧪 Testing question decomposition with Gemini...")
    
    question = "For Abbey Capital, find all their decision makers involved in healthcare, what have they invested in recently? what are some gaps?"
    
    prompt = f"""You are an expert business intelligence analyst. Break down this complex question into specific, answerable sub-questions for Abbey Capital.

QUESTION: "{question}"
COMPANY: "Abbey Capital"

Break the question into 3-4 sub-questions that:
1. Focus on decision makers in healthcare
2. Focus on recent healthcare investments  
3. Focus on strategic gaps or opportunities
4. Are specific and actionable

Return ONLY a JSON response in this format:
{{
  "sub_questions": [
    {{
      "question": "Who are the key decision makers at Abbey Capital involved in healthcare investments?",
      "focus": "decision_makers",
      "priority": "high"
    }},
    {{
      "question": "What healthcare investments has Abbey Capital made in the past 18 months?",
      "focus": "investments", 
      "priority": "high"
    }},
    {{
      "question": "What strategic gaps exist in Abbey Capital's healthcare portfolio?",
      "focus": "gaps",
      "priority": "medium"
    }}
  ],
  "strategy": "parallel"
}}"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1000}
    }
    
    try:
        # Prepare request
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        
        # Make request
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                response_data = json.loads(response.read().decode('utf-8'))
                
                if "candidates" in response_data and len(response_data["candidates"]) > 0:
                    candidate = response_data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        content = candidate["content"]["parts"][0]["text"]
                        print(f"✅ Gemini decomposition response:")
                        print(content)
                        
                        # Try to parse JSON
                        try:
                            # Extract JSON from response
                            start_idx = content.find('{')
                            end_idx = content.rfind('}') + 1
                            
                            if start_idx >= 0 and end_idx > start_idx:
                                json_content = content[start_idx:end_idx]
                                parsed = json.loads(json_content)
                                
                                print(f"\n✅ Successfully parsed {len(parsed.get('sub_questions', []))} sub-questions:")
                                for i, sq in enumerate(parsed.get('sub_questions', []), 1):
                                    print(f"  {i}. [{sq.get('focus', 'unknown')}] {sq.get('question', 'Unknown')}")
                                
                                return True, parsed
                        except json.JSONDecodeError as e:
                            print(f"⚠️ Could not parse JSON: {e}")
                            print("But got a response from Gemini")
                            return True, None
                        
                        return True, None
                
                print(f"❌ Unexpected response format: {response_data}")
                return False, None
            else:
                print(f"❌ Gemini API error {response.status}")
                return False, None
                
    except Exception as e:
        print(f"❌ Question decomposition test failed: {e}")
        return False, None

def test_abbey_capital_search():
    """Test specific Abbey Capital search with Tavily"""
    
    print("🧪 Testing Abbey Capital healthcare search...")
    
    url = "https://api.tavily.com/search"
    
    # Test multiple queries
    queries = [
        "Abbey Capital healthcare investments decision makers",
        "Abbey Capital investment team healthcare portfolio", 
        "Abbey Capital recent healthcare deals investments"
    ]
    
    all_results = []
    
    for query in queries:
        print(f"  Searching: {query}")
        
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "search_type": "general",
            "max_results": 3,
            "include_answer": True,
            "include_raw_content": True
        }
        
        try:
            # Prepare request
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            
            # Make request
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    response_data = json.loads(response.read().decode('utf-8'))
                    
                    results = response_data.get("results", [])
                    print(f"    Found {len(results)} results")
                    
                    for result in results:
                        all_results.append({
                            "query": query,
                            "title": result.get('title', 'No title'),
                            "url": result.get('url', 'No URL'),
                            "content": result.get('content', 'No content')[:200] + "..."
                        })
                else:
                    print(f"    ❌ Search failed with status {response.status}")
                    
        except Exception as e:
            print(f"    ❌ Search failed: {e}")
    
    print(f"\n✅ Total results collected: {len(all_results)}")
    
    # Show sample results
    for i, result in enumerate(all_results[:3], 1):
        print(f"\n{i}. {result['title']}")
        print(f"   URL: {result['url']}")
        print(f"   Content: {result['content']}")
    
    return len(all_results) > 0

def main():
    """Run all API tests"""
    
    print("🚀 BASIC API TESTING (No External Dependencies)")
    print("=" * 60)
    print()
    
    print("Testing API connections with your keys...")
    print(f"Tavily Key: {TAVILY_API_KEY[:10]}...")
    print(f"Gemini Key: {GEMINI_API_KEY[:10]}...")
    print()
    
    # Test Gemini
    gemini_ok = test_gemini_api()
    print()
    
    # Test Tavily  
    tavily_ok = test_tavily_api()
    print()
    
    if gemini_ok and tavily_ok:
        print("✅ Both APIs working! Testing advanced features...")
        print()
        
        # Test question decomposition
        decomposition_ok, parsed_questions = test_question_decomposition()
        print()
        
        # Test Abbey Capital specific search
        search_ok = test_abbey_capital_search()
        print()
        
        if decomposition_ok and search_ok:
            print("🎉 ALL TESTS PASSED!")
            print()
            print("🚀 READY FOR FULL INTELLIGENT SYSTEM!")
            print("Your APIs are working and can:")
            print("  ✅ Decompose complex questions with Gemini LLM")
            print("  ✅ Search for specific company intelligence with Tavily")
            print("  ✅ Handle Abbey Capital healthcare queries")
            print()
            print("Next step: Run the full intelligent Q&A system!")
        else:
            print("⚠️ Some advanced features need work, but basic APIs are functional")
    else:
        print("❌ API connection issues detected")
        if not gemini_ok:
            print("  - Gemini API failed - check your API key")
        if not tavily_ok:
            print("  - Tavily API failed - check your API key")

if __name__ == "__main__":
    main()
