#!/bin/bash
# UserPromptSubmit hook for keyword-based skill activation
#
# This hook analyzes user prompts and automatically injects skill activation
# commands based on keyword matching from skill-rules.json
#
# Complementary to skill-forced-eval-hook.sh
# This approach is faster and more targeted than forced eval
#
# Installation: Configured via .claude/settings.json

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/../config/skill-rules.json"

# Read user prompt from stdin
USER_PROMPT=$(cat)

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "$USER_PROMPT"
    exit 0
fi

# Function to check if prompt contains keyword (case-insensitive)
contains_keyword() {
    local prompt="$1"
    local keyword="$2"
    echo "$prompt" | grep -iq "$keyword"
}

# Extract skill configurations and check for matches
MATCHED_SKILLS=()
CRITICAL_SKILLS=()

# Parse JSON and match keywords
# Using Python for JSON parsing (more reliable than jq)
MATCHES=$(python3 <<EOF
import json
import sys
import re

prompt = """$USER_PROMPT""".lower()

try:
    with open('$CONFIG_FILE', 'r') as f:
        config = json.load(f)

    matched = []
    critical = []

    for skill_name, skill_config in config.get('skills', {}).items():
        keywords = skill_config.get('keywords', [])
        priority = skill_config.get('priority', 'low')
        force = skill_config.get('force_activation', False)

        # Check if any keyword matches
        for keyword in keywords:
            if keyword.lower() in prompt:
                matched.append(skill_name)
                if priority in ['critical', 'high'] or force:
                    critical.append(skill_name)
                break

    # Output matched skills (one per line)
    for skill in matched:
        print(f"MATCH:{skill}")

    # Output critical skills
    for skill in critical:
        print(f"CRITICAL:{skill}")

except Exception as e:
    # If parsing fails, just output nothing
    pass
EOF
)

# Parse matches
while IFS= read -r line; do
    if [[ $line == MATCH:* ]]; then
        skill="${line#MATCH:}"
        MATCHED_SKILLS+=("$skill")
    elif [[ $line == CRITICAL:* ]]; then
        skill="${line#CRITICAL:}"
        CRITICAL_SKILLS+=("$skill")
    fi
done <<< "$MATCHES"

# If no skills matched, just pass through the original prompt
if [ ${#MATCHED_SKILLS[@]} -eq 0 ]; then
    echo "$USER_PROMPT"
    exit 0
fi

# Build activation instructions
ACTIVATION_HEADER=""

if [ ${#CRITICAL_SKILLS[@]} -gt 0 ]; then
    ACTIVATION_HEADER+="🚨 CRITICAL: The following skills MUST be activated for this request:\n\n"
    for skill in "${CRITICAL_SKILLS[@]}"; do
        ACTIVATION_HEADER+="- **$skill** (MANDATORY)\n"
    done
    ACTIVATION_HEADER+="\n"
fi

if [ ${#MATCHED_SKILLS[@]} -gt ${#CRITICAL_SKILLS[@]} ]; then
    ACTIVATION_HEADER+="💡 Recommended skills detected:\n\n"
    for skill in "${MATCHED_SKILLS[@]}"; do
        # Skip if already in critical list
        if [[ ! " ${CRITICAL_SKILLS[@]} " =~ " ${skill} " ]]; then
            ACTIVATION_HEADER+="- $skill\n"
        fi
    done
    ACTIVATION_HEADER+="\n"
fi

ACTIVATION_HEADER+="🎯 INSTRUCTION: Use the Skill tool IMMEDIATELY before proceeding:\n\n"
ACTIVATION_HEADER+="\`\`\`\n"
for skill in "${MATCHED_SKILLS[@]}"; do
    ACTIVATION_HEADER+="Skill(skill=\"$skill\")\n"
done
ACTIVATION_HEADER+="\`\`\`\n\n"
ACTIVATION_HEADER+="⚠️ IMPORTANT: Do NOT start implementation without activating these skills.\n"
ACTIVATION_HEADER+="The skills contain critical workflows and standards that MUST be followed.\n\n"
ACTIVATION_HEADER+="---\n\n"

# Output modified prompt
echo -e "${ACTIVATION_HEADER}${USER_PROMPT}"
