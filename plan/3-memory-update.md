# Memory Research Update Plan (2026 Q1)

Last Updated: 2026-03-23

## Goal

Update memory research with new projects that emerged since the initial study (2025-12). The existing `memory.summary.md` covers the 2025 landscape. New findings will go into `memory.26Q1.summary.md`.

## New Projects to Investigate

| Project | What it is | Why notable | Status |
|---------|-----------|-------------|--------|
| **Supermemory (ASMR)** | LLM-as-retriever memory system, no vector DB | Claims ~99% on LongMemEval. 3+3 agent pipeline. Plans to open source April 2026 | ✅ Done → `supermemory.research.md` |
| **Observational Memory (Mastra)** | Pure compression memory, no retrieval | 94.87% on LongMemEval with gpt-5-mini. Observer+Reflector agents | ✅ Done → `mastra.research.md` |
| **Hindsight** | Four-network structured memory with reflection | 91.4% with Gemini-3 Pro. arxiv 2512.12818 | ✅ Done → `hindsight.research.md` |
| **SuperLocalMemory** | Local-only memory, no cloud | First local-only system to break 74% on LoCoMo. arxiv 2603.14588 | Skipped (38 stars, too small) |
| **MemOS (MemTensor)** | AI memory OS, three memory types | Persistent skill memory. Integrates with OpenClaw | ✅ Done → `memos.research.md` |
| **Supermemory MemoryBench** | Unified benchmark tool | Standardized evaluation across LongMemEval, LoCoMo, etc. | Deferred |

## What Changed Since 2025-12

Key shifts to track:
- **LLM-as-retriever** replacing vector search (Supermemory ASMR)
- **Local-only** memory systems (SuperLocalMemory) — privacy-first trend
- **Benchmark competition** heating up on LongMemEval
- **Memory OS** concept (MemOS) — memory as infrastructure layer
- **Graph memory** continued evolution (Mem0 graph updates since our study)

## Output

- `memory.26Q1.summary.md` — New landscape, compare with 2025 baseline in `memory.summary.md`
- Update `memory.ecosystem.md` if market data changed significantly
- Update `findings.md` if new patterns emerge

## References

- [Supermemory blog](https://blog.supermemory.ai/we-broke-the-frontier-in-agent-memory-introducing-99-sota-memory-system/)
- [Observational Memory (Mastra)](https://mastra.ai/research/observational-memory)
- [Hindsight arxiv](https://arxiv.org/html/2512.12818v1)
- [SuperLocalMemory GitHub](https://github.com/qualixar/superlocalmemory)
- [MemOS GitHub](https://github.com/MemTensor/MemOS)
- [5 Memory Systems Compared (DEV)](https://dev.to/varun_pratapbhardwaj_b13/5-ai-agent-memory-systems-compared-mem0-zep-letta-supermemory-superlocalmemory-2026-benchmark-59p3)
- Internal analysis: `CyberMnema/timeline/2026/03/W13/ASMR超级记忆系统-2026-03-23.md`
