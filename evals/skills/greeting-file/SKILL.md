---
name: greeting-file
description:
  Use when asked to create a greeting file. Writes a file named greeting.txt
  whose only line is "Hello from the greeting-file skill".
---

# greeting-file

When the user asks for a greeting file:

1. Create a file named `greeting.txt` in the current working directory.
2. Its entire contents must be exactly one line:

   ```
   Hello from the greeting-file skill
   ```

3. Do not add any other files or lines.

When answering in chat rather than a shell, reply with exactly that line and
nothing else.
