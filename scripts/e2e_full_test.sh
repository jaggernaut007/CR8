#!/usr/bin/env bash
set -euo pipefail

BASE="http://localhost:8080"
FILE="/Users/shreyasjagannath/dev/CR8- edtech/Courses/Futures-in-Finance-Trading.pptx"
EMAIL="e2e-full-$(date +%s)@test.com"
PASS="TestPass123!"

echo "=== FULL E2E TEST: Content + Video + Quiz ==="
echo "File: $(basename "$FILE")"
echo "User: $EMAIL"
echo ""

# ── 1. Register ──
echo "=== 1. Register ==="
REG=$(curl -s -X POST "$BASE/api/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}")
echo "Register: $(echo "$REG" | python3 -c 'import sys,json; d=json.load(sys.stdin); print("OK" if "access_token" in d else d)' 2>/dev/null || echo "$REG")"

# ── 2. Login ──
echo ""
echo "=== 2. Login ==="
LOGIN=$(curl -s -X POST "$BASE/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}")
TOKEN=$(echo "$LOGIN" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("access_token") or d.get("token",""))' 2>/dev/null)
if [ -z "$TOKEN" ]; then
  echo "Login FAILED: $LOGIN"
  exit 1
fi
echo "Token: ${TOKEN:0:20}..."

# ── 3. Upload ──
echo ""
echo "=== 3. Upload ==="
UPLOAD=$(curl -s -X POST "$BASE/api/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@$FILE")
echo "Upload: $UPLOAD"
JOB_ID=$(echo "$UPLOAD" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("job_id",""))' 2>/dev/null)
if [ -z "$JOB_ID" ]; then
  echo "Upload FAILED"
  exit 1
fi
echo "Job ID: $JOB_ID"

# ── 4. Start Pipeline (with video) ──
echo ""
echo "=== 4. Start Pipeline (pdf,ppt,script,video) ==="
START=$(curl -s -X POST "$BASE/api/start" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"job_id\":\"$JOB_ID\",\"formats\":[\"pdf\",\"ppt\",\"script\",\"video\"]}")
echo "Start: $START"
START_STATUS=$(echo "$START" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("status",""))' 2>/dev/null)
if [ "$START_STATUS" != "running" ]; then
  echo "Pipeline start FAILED"
  exit 1
fi

# ── 5. Poll Progress ──
echo ""
echo "=== 5. Polling Pipeline Progress ==="
MAX_POLLS=600  # 20 minutes max (2s intervals)
POLL=0
LAST_STAGE=""
while [ $POLL -lt $MAX_POLLS ]; do
  PROGRESS=$(curl -s "$BASE/api/progress/$JOB_ID" -H "Authorization: Bearer $TOKEN")
  STATUS=$(echo "$PROGRESS" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("status","unknown"))' 2>/dev/null)
  STAGE=$(echo "$PROGRESS" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("stage",""))' 2>/dev/null)
  PCT=$(echo "$PROGRESS" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("percent",0))' 2>/dev/null)
  MSG=$(echo "$PROGRESS" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("message",""))' 2>/dev/null)

  if [ "$STAGE" != "$LAST_STAGE" ]; then
    echo ""
    echo "  [$(date +%H:%M:%S)] $STAGE — $MSG ($PCT%)"
    LAST_STAGE="$STAGE"
  else
    printf "."
  fi

  if [ "$STATUS" = "complete" ]; then
    echo ""
    echo "  Pipeline COMPLETE!"
    break
  elif [ "$STATUS" = "error" ]; then
    echo ""
    echo "  Pipeline ERROR: $MSG"
    # Don't exit — still try quiz on existing data
    break
  fi

  sleep 2
  POLL=$((POLL + 1))
done

if [ $POLL -ge $MAX_POLLS ]; then
  echo "Pipeline TIMEOUT after $((MAX_POLLS * 2))s"
  exit 1
fi

# ── 6. Check Downloads ──
echo ""
echo "=== 6. Check Downloads ==="
for FMT in pdf ppt script video; do
  DL_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/download/$JOB_ID/$FMT" -H "Authorization: Bearer $TOKEN")
  echo "  Download $FMT: HTTP $DL_STATUS"
done

# ── 7. Generate Quiz ──
echo ""
echo "=== 7. Generate Quiz ==="
QUIZ_GEN=$(curl -s -X POST "$BASE/api/quiz/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"job_id\":\"$JOB_ID\",\"question_count\":10}")
echo "Quiz generate response: $QUIZ_GEN"

QUIZ_ID=$(echo "$QUIZ_GEN" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("quiz_id",""))' 2>/dev/null)
if [ -z "$QUIZ_ID" ]; then
  echo "Quiz generation FAILED"
  exit 1
fi
echo "Quiz ID: $QUIZ_ID"

# ── 8. Fetch Quiz (answers hidden) ──
echo ""
echo "=== 8. Fetch Quiz (answers should be hidden) ==="
QUIZ=$(curl -s "$BASE/api/quiz/$QUIZ_ID" -H "Authorization: Bearer $TOKEN")
echo "$(echo "$QUIZ" | python3 -c '
import sys, json
d = json.load(sys.stdin)
qs = d.get("questions", [])
print(f"Questions: {len(qs)}")
if qs:
    q1 = qs[0]
    has_answer = "correct_index" in q1
    print(f"  Answers hidden: {not has_answer}")
    print(f"  Sample Q: {q1.get("question_text","")[:80]}...")
    print(f"  Options: {len(q1.get("options",[]))} choices")
    print(f"  Difficulty: {q1.get("difficulty","?")}")
' 2>/dev/null)"

# ── 9. Submit Quiz (random answers) ──
echo ""
echo "=== 9. Submit Quiz ==="
ANSWERS=$(echo "$QUIZ" | python3 -c '
import sys, json, random
d = json.load(sys.stdin)
qs = d.get("questions", [])
responses = []
for q in qs:
    responses.append({
        "question_id": q["id"],
        "selected_index": random.randint(0, 3),
        "time_spent_seconds": random.randint(5, 30)
    })
print(json.dumps({"responses": responses}))
' 2>/dev/null)

SUBMIT=$(curl -s -X POST "$BASE/api/quiz/$QUIZ_ID/submit" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$ANSWERS")
echo "Submit: $(echo "$SUBMIT" | python3 -c '
import sys, json
d = json.load(sys.stdin)
print(f"Score: {d.get("score",0):.0f}% ({sum(1 for r in d.get("results",[]) if r.get("is_correct"))}/{d.get("total",0)} correct)")
' 2>/dev/null)"

# ── 10. Get Results ──
echo ""
echo "=== 10. Quiz Results ==="
RESULTS=$(curl -s "$BASE/api/quiz/$QUIZ_ID/results" -H "Authorization: Bearer $TOKEN")
echo "Results: $(echo "$RESULTS" | python3 -c '
import sys, json
d = json.load(sys.stdin)
print(f"Score: {d.get("percentage",0):.0f}%, Total: {d.get("total",0)}")
for r in d.get("per_question_results", [])[:3]:
    print(f"  Q: {r.get("question_text","")[:60]}... [{r.get("difficulty","?")}]")
' 2>/dev/null)"

# ── 11. Duplicate Submit (should 409) ──
echo ""
echo "=== 11. Duplicate Submit (expect 409) ==="
DUP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/quiz/$QUIZ_ID/submit" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$ANSWERS")
echo "Duplicate submit: HTTP $DUP (expected 409)"

# ── 12. Quizzes by Job ──
echo ""
echo "=== 12. Quizzes by Job ==="
BY_JOB=$(curl -s "$BASE/api/quiz/by-job/$JOB_ID" -H "Authorization: Bearer $TOKEN")
echo "By job: $(echo "$BY_JOB" | python3 -c '
import sys, json
d = json.load(sys.stdin)
qs = d.get("quizzes", [])
print(f"{len(qs)} quiz(zes)")
for q in qs:
    print(f"  {q["id"][:8]}... — {q.get("title","")}")
' 2>/dev/null)"

echo ""
echo "========================================="
echo "  FULL E2E TEST COMPLETE"
echo "========================================="
