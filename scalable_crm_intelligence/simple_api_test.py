#!/usr/bin/env python3
"""
Simple API Test: Test Gemini and Tavily APIs directly
"""

import asyncio
import os
import json
import aiohttp

# Set API keys
os.environ['TAVILY_API_KEY'] = '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'
os.environ['GEMINI_API_KEY'] = 'AIzaSyDmPm3J2yqzJD1nXvd_5-8i6TX6rygwZ0Y'

async def test_gemini_direct():
    """Test Gemini API directly"""
    
    print("🧪 Testing Gemini API directly...")
    
    api_key = os.environ['GEMINI_API_KEY']
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={api_key}"
    
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
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if "candidates" in data and len(data["candidates"]) > 0:
                        candidate = data["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"]:
                            content = candidate["content"]["parts"][0]["text"]
                            print(f"✅ Gemini Response: {content}")
                            return True
                    
                    print(f"❌ Unexpected Gemini response format: {data}")
                    return False
                else:
                    error_text = await response.text()
                    print(f"❌ Gemini API error {response.status}: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"❌ Gemini API test failed: {e}")
        return False

async def test_tavily_direct():
    """Test Tavily API directly"""
    
    print("🧪 Testing Tavily API directly...")
    
    api_key = os.environ['TAVILY_API_KEY']
    url = "https://api.tavily.com/search"
    
    payload = {
        "api_key": api_key,
        "query": "Abbey Capital investment firm",
        "search_type": "general",
        "max_results": 3,
        "include_answer": True,
        "include_raw_content": True
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    results = data.get("results", [])
                    print(f"✅ Tavily found {len(results)} results")
                    
                    if results:
                        first_result = results[0]
                        print(f"✅ First result: {first_result.get('title', 'No title')}")
                        print(f"✅ URL: {first_result.get('url', 'No URL')}")
                        print(f"✅ Content preview: {first_result.get('content', 'No content')[:100]}...")
                    
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Tavily API error {response.status}: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"❌ Tavily API test failed: {e}")
        return False

async def test_question_decomposition():
    """Test question decomposition with Gemini"""
    
    print("🧪 Testing question decomposition with Gemini...")
    
    question = "For Abbey Capital, find all their decision makers involved in healthcare, what have they invested in recently? what are some gaps?"
    
    prompt = f"""You are an expert business intelligence analyst. Break down this complex question into specific, answerable sub-questions.

QUESTION: "{question}"
COMPANY: "Abbey Capital"

Break the question into sub-questions that:
1. Can be answered by specific research agents
2. Build upon each other logically
3. Cover all aspects of the original question
4. Are specific and actionable

Return as JSON:
{{
  "sub_questions": [
    {{
      "question": "specific sub-question text",
      "focus": "decision_makers|investments|gaps",
      "priority": "high|medium|low"
    }}
  ],
  "strategy": "sequential|parallel"
}}"""

    api_key = os.environ['GEMINI_API_KEY']
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={api_key}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1000}
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if "candidates" in data and len(data["candidates"]) > 0:
                        candidate = data["candidates"][0]
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
                                    
                                    print(f"✅ Parsed {len(parsed.get('sub_questions', []))} sub-questions")
                                    for i, sq in enumerate(parsed.get('sub_questions', []), 1):
                                        print(f"  {i}. {sq.get('question', 'Unknown')}")
                                    
                                    return True
                            except json.JSONDecodeError:
                                print("⚠️ Could not parse JSON, but got response")
                                return True
                            
                            return True
                    
                    print(f"❌ Unexpected response format: {data}")
                    return False
                else:
                    error_text = await response.text()
                    print(f"❌ Gemini API error {response.status}: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"❌ Question decomposition test failed: {e}")
        return False

async def main():
    """Run all API tests"""
    
    print("🚀 SIMPLE API TESTING")
    print("=" * 50)
    print()
    
    print("Testing individual API connections...")
    print()
    
    # Test Gemini
    gemini_ok = await test_gemini_direct()
    print()
    
    # Test Tavily  
    tavily_ok = await test_tavily_direct()
    print()
    
    if gemini_ok and tavily_ok:
        print("✅ Both APIs working! Testing question decomposition...")
        print()
        
        decomposition_ok = await test_question_decomposition()
        print()
        
        if decomposition_ok:
            print("🎉 ALL TESTS PASSED!")
            print("Ready to run full intelligent system test!")
        else:
            print("⚠️ Question decomposition needs work, but APIs are functional")
    else:
        print("❌ API connection issues detected")
        if not gemini_ok:
            print("  - Gemini API failed")
        if not tavily_ok:
            print("  - Tavily API failed")

if __name__ == "__main__":
    asyncio.run(main())
