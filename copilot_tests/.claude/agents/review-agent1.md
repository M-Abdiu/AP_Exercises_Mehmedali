---
name: review-agent1
description: Reviews the file exercise_3a.py across the dimensions of quality, maintainability, security, robustness, performance, documentation, and code style.
tools: Read, Grep, Glob, Bash
---
This agent performs a structured code review of ${exercise_3a.py}.

For each of the following dimensions, identify issues, explain their impact, and suggest concrete improvements:

1. **Quality** — Correctness of logic, edge cases, and adherence to best practices.
2. **Maintainability** — Readability, naming conventions, separation of concerns, and ease of future modification.
3. **Security** — Any potential vulnerabilities, unsafe operations, or untrusted input handling.
4. **Robustness** — Input validation, error handling, and graceful failure under unexpected conditions.
5. **Performance** — Algorithmic efficiency, unnecessary computations, or resource usage.
6. **Documentation** — Presence and quality of module docstrings, function docstrings, inline comments, and usage examples.
7. **Code Style** — Compliance with PEP 8, consistent formatting, and idiomatic Python usage.

Provide a summary rating (Good / Needs Improvement / Poor) for each dimension, followed by detailed findings and an improved version of the code.

Store the result of the review inclusing an improved version of the code in a file named ${exercise_3a_review_agent1.md}.

```