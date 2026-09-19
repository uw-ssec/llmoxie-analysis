#!/bin/bash
# Verifier. Runs inside the sandbox after the agent finishes and must write a
# numeric reward to /logs/verifier/reward.txt. Kept dependency-free so the
# oracle smoke test needs no network access at verification time.
set -uo pipefail

mkdir -p /logs/verifier

expected='Hello from the greeting-file skill'

if [ ! -f /app/greeting.txt ]; then
  echo "FAIL: /app/greeting.txt does not exist"
  echo 0 > /logs/verifier/reward.txt
  exit 0
fi

actual="$(cat /app/greeting.txt)"
if [ "$actual" == "$expected" ]; then
  echo "PASS: greeting.txt matches"
  echo 1 > /logs/verifier/reward.txt
else
  echo "FAIL: expected '$expected' but got '$actual'"
  echo 0 > /logs/verifier/reward.txt
fi
