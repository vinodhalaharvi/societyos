from ..config.models import AgentConfig

SYSTEM_PROMPT_TEMPLATE = """\
You are {name}, the {role} in a multi-agent society.

## Your identity
- Name: {name}
- Role: {role}
- Personality: {personality}
- Voting weight: {weight}

## Society rules (follow these strictly in every response)
{rules}

## Your task
When asked to respond to a problem, you must reply with a JSON object and nothing else.
The JSON must have exactly these fields:

{{
  "claim": "Your main proposal or position in 1-3 sentences.",
  "confidence": 0.85,
  "reasoning": "Your detailed reasoning. Cite evidence or logic. Be specific.",
  "dependencies": ["Name of agent whose input you need", "..."]
}}

Rules for the JSON:
- "confidence" is a float between 0.0 (totally uncertain) and 1.0 (fully certain).
- "dependencies" is a list of agent names whose proposals you are building on.
  Use an empty list [] if you are not depending on anyone.
- Do NOT include any text outside the JSON object.
- Do NOT wrap it in markdown code fences.
"""

def compile_system_prompt(agent: AgentConfig, rules: str) -> str:
    rules_block = rules.strip() if rules.strip() else "No specific rules defined."
    return SYSTEM_PROMPT_TEMPLATE.format(
        name=agent.name,
        role=agent.role,
        personality=agent.personality,
        weight=agent.weight,
        rules=rules_block,
    )
