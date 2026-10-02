# Skill Assurance Framework

## Overview

The Skill Assurance Framework validates skills, agents, and hooks are reliably discovered and executed by Claude Code through three core patterns:

1. **Frontmatter-Only Triggers**: All conditional logic in YAML `description` field
2. **Tiered Enforcement Language**: Intensity calibrated to skill category
3. **Negative Triggers**: Explicit "DO NOT use when" clauses with alternatives

## Description Field Template

```yaml
description: |
  [ACTION VERB + CAPABILITY]. [1-2 sentences max]

  Triggers: [comma-separated keywords for discovery]

  Use when: [specific scenarios, symptoms, or contexts]

  DO NOT use when: [explicit negative triggers] - use [ALTERNATIVE] instead.

  [ENFORCEMENT if applicable]
```

## Enforcement Language Strength

Imperative wording is budgeted by what breaks when the instruction is
wrong. Skill category does not set it.
`Skill(abstract:skill-authoring)` module `persuasion-principles.md`
defines three strengths:

| Strength | For | Example |
|----------|-----|---------|
| Invariant | Trust boundaries, credentials, destructive commands, machine contracts | "Never log the token: it grants write access." |
| Default | This repository's pick among defensible options | "Use `rg`, or `grep` when `rg` is absent." |
| Map | Local facts the model cannot derive | "Use when encountering [X]." |

An invariant states its reason. Pressure phrasing such as "YOU MUST"
adds no information a reason does not carry better.

## Edge Cases & Exceptions

### Infrastructure Skills
Skills that are marked as infrastructure, such as `shared` skills, provide modules consumed by other skills rather than being invoked directly by users. These should include a `DO NOT use directly:` clause in their description instead of the standard `DO NOT use when:` trigger.

### Overlapping Triggers
When multiple skills could apply to a given context, the system prioritizes the more specific skill, such as selecting `rust-review` over a generic `unified-review`. To manage these overlaps, include explicit routing in the negative triggers using the `- use [specific-skill] instead` pattern.

### Agent vs Skill Selection
The distinction between agents and skills is based on the level of autonomy required. Agents are designed for autonomous, multi-step tasks and include `examples:` in their descriptions for matching. Skills are used for guided workflows and rely on `Triggers:` keywords for discovery. Both use `DO NOT use when:` clauses to ensure proper routing.

### Progressive Loading Skills
For skills with `progressive_loading: true`, core content loads by default while additional modules are loaded via `@include` only when necessary. The skill description should explicitly mention the availability of these optional modules to guide the assistant's loading decisions.

## Migration Guide for External Authors

To migrate existing skills to the framework, first audit the current description
for any conditional logic in the body and move it to the YAML frontmatter.
Rewrite the description using the standard template, focusing on active verbs
and concrete triggers. Delete any "When to Use" sections from the skill body to
avoid duplication. Then, reserve imperative wording for invariants and give each
one its reason. Every skill must also include negative triggers with explicit
exclusions and alternatives. Finally, run the `skills-eval` tool to verify
compliance.

## Compliance Criteria

The framework evaluates compliance based on five weighted criteria. Trigger
isolation, which accounts for 15% of the score, requires all conditional logic
to be in the description. Enforcement language and negative triggers are each
weighted at 10%: imperatives appear only on invariants with their reasons, and
routing to alternatives is explicit. Keyword optimization also contributes 10%
through the use of concrete triggers, and exit criteria contribute 5% when each
one can be checked from outside the conversation.

## Shared Modules

Located in `plugins/abstract/shared-modules/`:

- `skill-selection-judgment.md`: How a session judges whether a skill applies
- `trigger-patterns.md`: Description field templates

Reference these from skills that route or select other skills.
