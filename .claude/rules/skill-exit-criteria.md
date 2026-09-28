---
description: Require Exit Criteria sections in SKILL.md files
alwaysApply: true
---

**Every new or modified SKILL.md must include an Exit Criteria
section!**

A skill without exit criteria is a skill the model cannot tell
when to stop. That is AP-7 (Vague Success Criteria), and the
April 2026 Karpathy-compliance audit found it in most of the
skills shipped at the time.

**Required format:**

```markdown
## Exit Criteria

- [ ] Concrete observable A
- [ ] Concrete observable B
- [ ] Failure mode N is detected and surfaced
```

Each criterion must be:

- **Concrete**: a state a reader can verify from outside the
  conversation (file exists, value parses, score above threshold)
- **Observable**: tied to a tool call, file path, or numeric
  threshold, not an internal feeling ("the skill feels complete")
- **Falsifiable**: removing the supporting code or doc must make
  at least one criterion fail

**When the rule applies:**

- Authoring a new SKILL.md
- Modifying an existing SKILL.md (add the section if missing)
- Reviewing a PR that touches SKILL.md files

**When it does not apply:**

- Module files (``modules/*.md``) inside a skill directory
- Reference documentation (``docs/``)
- Slash command files (``commands/*.md``); commands have their own
  argument and output contract conventions

**Checking it:**

`plugins/abstract/tests/test_every_skill_has_exit_criteria.py`
fails for any `plugins/*/skills/*/SKILL.md` without the section,
and names each file.

**References:**

- Issue #454 (origin)
- Discussion #449 (April 2026 skill audit synthesis)
- Karpathy AP-7: Vague Success Criteria
- ``plugins/imbue/skills/karpathy-principles/SKILL.md``
