#!/bin/bash
# Reference solution, executed by the built-in `oracle` agent. It should do
# exactly what a well-behaved agent following the skill would do.
set -euo pipefail

printf 'Hello from the greeting-file skill\n' > /app/greeting.txt
