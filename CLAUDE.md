# LLM Agent Research

See [README.md](./README.md) for full repository structure index and file descriptions.

## Research Directions

1. **Memory** - LLM agent memory frameworks, vector databases, coding assistant memory implementations, reverse engineering of commercial products (ChatGPT, Claude). Existing research is in `*.research.md` files, `reverse-engineer/`, and `agent-cli/`.
2. **Context** - How agents assemble and manage context within a conversation: token generation, context window construction, prompt stitching strategies. See [plan/1-context-research.md](./plan/1-context-research.md) for detailed plan. Targets: Pi, OpenClaw, Gemini CLI (open source); Claude Code, Codex (reverse engineering).
3. **Learning** (TODO) - Can models learn after deployment? Continual learning, catastrophic forgetting, personalized models. Focus on: academic survey of continual learning for LLMs, any production systems that do user-level adaptation (fine-tuning, LoRA, adapter). Note: no open-source coding agent currently does this — all use external memory instead of weight updates.
