#!/usr/bin/env python3
"""
Test Tavily API connection and search functionality
"""

import os
import requests
import json

def test_tavily_basic():
    """Test basic Tavily API connection"""
    api_key = os.getenv('TAVILY_API_KEY')
    if not api_key:
        print("❌ TAVILY_API_KEY not set")
        return False

    print("🔑 Testing basic Tavily API connection...")

    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": "Apple Inc company overview",
                "max_results": 3,
                "include_answer": True,
                "include_raw_content": False
            },
            timeout=10
        )

        print(f"Response status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ API call successful!")
            print(f"Results found: {len(result.get('results', []))}")

            if result.get('results'):
                for i, res in enumerate(result['results'][:2]):
                    print(f"\nResult {i+1}:")
                    print(f"  Title: {res.get('title', 'N/A')}")
                    print(f"  URL: {res.get('url', 'N/A')}")
                    print(f"  Content: {res.get('content', '')[:100]}...")

            return True
        else:
            print(f"❌ API error: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

def test_company_search():
    """Test company-specific search"""
    api_key = os.getenv('TAVILY_API_KEY')
    if not api_key:
        return False

    print("\n🏢 Testing company search...")

    companies = [
        "3EDGE Asset Management",
        "747 Capital"
    ]

    for company in companies:
        print(f"\n🔍 Searching for: {company}")

        try:
            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": f'"{company}" leadership team executives',
                    "max_results": 5,
                    "include_answer": True,
                    "include_raw_content": False
                },
                timeout=15
            )

            if response.status_code == 200:
                result = response.json()
                results = result.get('results', [])

                print(f"  ✅ Found {len(results)} results")

                for i, res in enumerate(results[:3]):
                    print(f"    {i+1}. {res.get('title', 'N/A')}")
                    print(f"       URL: {res.get('url', 'N/A')}")
                    content = res.get('content', '')
                    if content:
                        # Try to extract executive names
                        lines = content.split('\n')
                        for line in lines[:3]:
                            if any(word in line.lower() for word in ['ceo', 'founder', 'president', 'director']):
                                print(f"       Content: {line.strip()}")
                                break
            else:
                print(f"  ❌ Error: {response.status_code}")

        except Exception as e:
            print(f"  ❌ Error: {e}")

        # Small delay between searches
        import time
        time.sleep(2)

def main():
    """Run all tests"""
    print("🧪 TAVILY API TEST SUITE")
    print("=" * 50)

    # Test 1: Basic connection
    basic_test = test_tavily_basic()

    if basic_test:
        # Test 2: Company searches
        test_company_search()

        print("\n" + "=" * 50)
        print("🎉 API TESTS COMPLETE!")
        print("If you see results above, the Tavily API is working correctly.")
        print("The deep intelligence scout should work now.")
    else:
        print("\n❌ API tests failed. Check your TAVILY_API_KEY.")

if __name__ == "__main__":
    main()
