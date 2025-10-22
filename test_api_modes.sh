#!/bin/bash

# Test script for RAG Report API - 3 Modes
# Usage: ./test_api_modes.sh [base_url]

BASE_URL="${1:-http://localhost:8000}"

echo "🧪 Testing RAG Report API"
echo "Base URL: $BASE_URL"
echo "=========================================="

# Sample transcript
TRANSCRIPT="Co: 你好，今天想聊什麼？\\nCl: 我最近對職涯方向感到困惑，不知道該往哪裡走。工作了三年，感覺沒有成長。\\nCo: 能具體說說你的困擾嗎？\\nCl: 我在做行銷企劃，但總覺得缺少核心專業，不知道未來要怎麼發展。"

echo ""
echo "📝 Test Transcript:"
echo "$TRANSCRIPT" | sed 's/\\n/\n/g'
echo ""
echo "=========================================="

# Test 1: Enhanced Mode
echo ""
echo "1️⃣ Testing ENHANCED mode..."
echo ""

curl -X POST "$BASE_URL/api/report/generate" \
  -H "Content-Type: application/json" \
  -d "{
    \"transcript\": \"$TRANSCRIPT\",
    \"mode\": \"enhanced\",
    \"num_participants\": 2,
    \"output_format\": \"json\"
  }" \
  -w "\nHTTP Status: %{http_code}\n" \
  -o /tmp/enhanced_response.json

if [ $? -eq 0 ]; then
  echo "✅ Enhanced mode response saved to /tmp/enhanced_response.json"
  echo "Mode: $(cat /tmp/enhanced_response.json | python3 -m json.tool | grep '\"mode\"' | head -1)"
  echo "Quality Score: $(cat /tmp/enhanced_response.json | python3 -m json.tool | grep 'total_score' | head -1)"
else
  echo "❌ Enhanced mode FAILED"
fi

echo ""
echo "=========================================="

# Test 2: Legacy Mode
echo ""
echo "2️⃣ Testing LEGACY mode..."
echo ""

curl -X POST "$BASE_URL/api/report/generate" \
  -H "Content-Type: application/json" \
  -d "{
    \"transcript\": \"$TRANSCRIPT\",
    \"mode\": \"legacy\",
    \"num_participants\": 2,
    \"output_format\": \"json\"
  }" \
  -w "\nHTTP Status: %{http_code}\n" \
  -o /tmp/legacy_response.json

if [ $? -eq 0 ]; then
  echo "✅ Legacy mode response saved to /tmp/legacy_response.json"
  echo "Mode: $(cat /tmp/legacy_response.json | python3 -m json.tool | grep '\"mode\"' | head -1)"
  echo "Quality Score: $(cat /tmp/legacy_response.json | python3 -m json.tool | grep 'total_score' | head -1)"
else
  echo "❌ Legacy mode FAILED"
fi

echo ""
echo "=========================================="

# Test 3: Comparison Mode
echo ""
echo "3️⃣ Testing COMPARISON mode..."
echo ""

curl -X POST "$BASE_URL/api/report/generate" \
  -H "Content-Type: application/json" \
  -d "{
    \"transcript\": \"$TRANSCRIPT\",
    \"mode\": \"comparison\",
    \"num_participants\": 2,
    \"output_format\": \"json\"
  }" \
  -w "\nHTTP Status: %{http_code}\n" \
  -o /tmp/comparison_response.json

if [ $? -eq 0 ]; then
  echo "✅ Comparison mode response saved to /tmp/comparison_response.json"
  echo "Mode: $(cat /tmp/comparison_response.json | python3 -m json.tool | grep '\"mode\"' | head -1)"
  echo "Legacy Score: $(cat /tmp/comparison_response.json | python3 -m json.tool | grep 'total_score' | head -2 | tail -1)"
  echo "Enhanced Score: $(cat /tmp/comparison_response.json | python3 -m json.tool | grep 'total_score' | tail -1)"
else
  echo "❌ Comparison mode FAILED"
fi

echo ""
echo "=========================================="
echo ""
echo "🎉 All tests completed!"
echo ""
echo "📁 Results saved to:"
echo "  - /tmp/enhanced_response.json"
echo "  - /tmp/legacy_response.json"
echo "  - /tmp/comparison_response.json"
echo ""
echo "💡 View formatted output:"
echo "  cat /tmp/enhanced_response.json | python3 -m json.tool | less"
echo ""
