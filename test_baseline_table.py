import sys
import os
sys.path.insert(0, '.')

# Set work mode env var
os.environ['PTANALYZER_MODE'] = 'work'
os.environ['POSTGRES_HOST'] = 'localhost'
os.environ['POSTGRES_PORT'] = '5432'
os.environ['POSTGRES_DB'] = 'ptanalyzer'
os.environ['POSTGRES_USER'] = 'appuser'
os.environ['POSTGRES_PASSWORD'] = 'securepassword123'

from src.analyzer import TestAnalyzer

# Initialize analyzer
analyzer = TestAnalyzer()

# Test baseline comparison with explicit table request
result = analyzer.ask('Show me a full transaction comparison table for LoadTest_20260304T060726Z with baseline including all metrics')

# Write answer to file for inspection
with open('/tmp/baseline_test_output.txt', 'w') as f:
    f.write(result['answer'])

print(f"Tools used: {result.get('tools_used', [])}")
print(f"\nAnswer length: {len(result['answer'])} chars")

# Check for table
if '|' in result['answer'] and 'Transaction' in result['answer']:
    print("✅ Table found in answer!")
    # Count table rows
    table_rows = len([line for line in result['answer'].split('\n') if line.strip().startswith('|') and '---' not in line])
    print(f"   Table has {table_rows} rows")
else:
    print("❌ No table found in answer")

print("\nFull answer written to /tmp/baseline_test_output.txt")
