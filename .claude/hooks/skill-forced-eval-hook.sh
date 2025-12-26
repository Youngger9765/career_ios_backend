#!/bin/bash
# UserPromptSubmit hook that forces explicit skill evaluation
#
# This hook requires Claude to explicitly evaluate each available skill
# before proceeding with implementation.
#
# Based on Scott Spence's research: 84% activation success rate
# Reference: https://scottspence.com/posts/how-to-make-claude-code-skills-activate-reliably
#
# Installation: Configured via .claude/settings.json

cat <<'EOF'
🎯 INSTRUCTION: MANDATORY SKILL ACTIVATION SEQUENCE

Step 1 - EVALUATE (do this in your response):
For each skill in <available_skills>, state: [skill-name] - YES/NO - [reason]

Step 2 - ACTIVATE (do this immediately after Step 1):
IF any skills are YES → Use Skill(skill="skill-name") tool for EACH relevant skill NOW
IF no skills are YES → State "No skills needed" and proceed

Step 3 - IMPLEMENT:
Only after Step 2 is complete, proceed with implementation.

CRITICAL RULES:
- You MUST call Skill() tool in Step 2. Do NOT skip to implementation.
- The evaluation (Step 1) is WORTHLESS unless you ACTIVATE (Step 2) the skills.
- NEVER proceed to Step 3 without completing Step 2.

Example of correct sequence:
```
Step 1 - EVALUATE:
- requirements-clarification: YES - user request lacks specific details
- tdd-workflow: YES - implementing new API endpoint
- debugging: NO - not a debugging task
- quality-standards: NO - not focused on refactoring

Step 2 - ACTIVATE:
[Skill tool calls made here]
Skill(skill="requirements-clarification")
Skill(skill="tdd-workflow")

Step 3 - IMPLEMENT:
[Implementation starts only after Step 2 is complete]
```

🚨 IMPORTANT: Skills marked as "CRITICAL" or "MANDATORY" in their descriptions MUST be activated if relevant.

EOF
