"""
Test Script for PubMearch Analyzer
Verifies that the transplanted framework works correctly.
"""
import sys
import os
import json
import logging

# Add the local directory to sys.path to simulate package structure
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from pubmearch.analyzer import PubMedAnalyzer

def test_analyzer():
    print("🧪 Starting PubMearch Analyzer Test...")
    
    results_dir = os.path.join(current_dir, "results")
    analyzer = PubMedAnalyzer(results_dir=results_dir)
    
    input_file_name = "test_data.json"
    input_path = os.path.join(results_dir, input_file_name)
    
    print(f"📖 Reading from {input_path}...")
    try:
        analysis = analyzer.generate_comprehensive_analysis(input_path)
        
        if "error" in analysis:
            print(f"❌ Error: {analysis['error']}")
            sys.exit(1)
            
        print("✅ Analysis Successful!")
        print(f"📄 Top Keywords: {[k['keyword'] for k in analysis['keyword_analysis']['top_keywords']]}")
        print(f"📈 Article Count: {analysis['article_count']}")
        
        # Save output
        output_path = os.path.join(results_dir, "test_output.json")
        with open(output_path, "w") as f:
            json.dump(analysis, f, indent=2)
        print(f"💾 Output saved to {output_path}")
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_analyzer()
