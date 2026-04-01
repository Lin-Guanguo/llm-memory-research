# Claude Code Buddy/Companion: Architecture Analysis

Last Updated: 2026-04-01

Sources:
- [ChinaSiro/claude-code-sourcemap](https://github.com/ChinaSiro/claude-code-sourcemap) — v2.1.88 source map extraction
- Live observation of `/buddy` command behavior (April 1, 2026 teaser window)
- Companion with [claude-code-sourcemap.research.md](./claude-code-sourcemap.research.md) for core architecture context

Research focus: How Claude Code implements a "virtual pet" companion feature as a side-channel inference system — its process model, billing separation, integration with the prompt cache architecture, and what it reveals about Anthropic's feature staging infrastructure.

For product design analysis (engagement mechanics, interaction model, gacha psychology, UX principles), see [claude-code-buddy.product.research.md](./claude-code-buddy.product.research.md).

---

## Background

On April 1, 2026, Claude Code users discovered a `/buddy` command that hatches a persistent ASCII art companion in the terminal. The companion sits beside the input box, occasionally reacts to conversations in a speech bubble, and responds when addressed by name. Anthropic explicitly stated it does not count toward personal usage quota.

The feature is gated behind `feature('BUDDY')` — a compile-time constant that controls dead-code elimination. In v2.1.88 (the leaked source map version), the feature gate evaluates to `false` for external builds, meaning **all buddy code is stripped from the compiled bundle**. However, the TypeScript source files are preserved in the source map's `sourcesContent` array, giving us full visibility into the implementation.

**Files found in source map** (6 of expected ~8+):

| File | Size | Purpose |
|------|------|---------|
| `src/buddy/types.ts` | 149 lines | Type definitions, rarity weights, species/eye/hat/stat enums |
| `src/buddy/companion.ts` | 134 lines | Mulberry32 PRNG, deterministic roll from userId, companion retrieval |
| `src/buddy/sprites.ts` | 514 lines | ASCII art bodies (18 species × 3 frames), hat overlays, face rendering |
| `src/buddy/prompt.ts` | 36 lines | Companion intro attachment for main model |
| `src/buddy/CompanionSprite.tsx` | ~370 lines | React Ink component: animation tick, speech bubble, pet hearts |
| `src/buddy/useBuddyNotification.tsx` | 98 lines | Teaser notification, date gates, trigger detection |

**Files missing from source map** (referenced but not extracted):
- `src/buddy/observer.ts` — the companion reaction generator (referenced in AppStateStore comment)
- `src/commands/buddy/index.ts` — the `/buddy` slash command handler (lazy-imported in commands.ts)

---

## 1. Data Model: Bones/Soul Separation

The companion's data is split into two categories with fundamentally different lifecycles:

### 1.1 CompanionBones (Deterministic, Never Persisted)

```typescript
type CompanionBones = {
  rarity: Rarity       // 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary'
  species: Species     // 18 species (duck, cat, dragon, axolotl, capybara, etc.)
  eye: Eye             // '·', '✦', '×', '◉', '@', '°'
  hat: Hat             // 'none' for common; crown/tophat/propeller/etc. for rare+
  shiny: boolean       // 1% chance
  stats: Record<StatName, number>  // DEBUGGING, PATIENCE, CHAOS, WISDOM, SNARK
}
```

Generated deterministically from `hash(userId + SALT)` using Mulberry32 PRNG:

```typescript
const SALT = 'friend-2026-401'

function roll(userId: string): Roll {
  const key = userId + SALT
  const rng = mulberry32(hashString(key))
  // ... deterministic species, eyes, hat, stats
}
```

**Rarity distribution** (weighted random via PRNG):

| Rarity | Weight | Floor stat | Hat? |
|--------|--------|-----------|------|
| common | 60% | 5 | No |
| uncommon | 25% | 15 | Yes |
| rare | 10% | 25 | Yes |
| epic | 4% | 35 | Yes |
| legendary | 1% | 50 | Yes |

**Stats system**: One peak stat (+50-80 above floor), one dump stat (-10 to +5 from floor), rest scattered. Higher rarity raises the floor for all stats.

### 1.2 CompanionSoul (Model-Generated, Persisted)

```typescript
type CompanionSoul = {
  name: string          // e.g., "Bane"
  personality: string   // personality description
}

type StoredCompanion = CompanionSoul & { hatchedAt: number }
```

Generated once during first `/buddy` invocation ("hatching"), stored in `~/.claude/config.json` under the `companion` key.

### 1.3 Why This Split?

From `companion.ts:121-123`:

> Bones are regenerated from hash(userId) on every read so species renames don't break stored companions and users can't edit their way to a legendary.

This is an **anti-tampering + forward-compatibility** design:

1. **Anti-cheat**: Editing `~/.claude/config.json` can only change name/personality, not rarity/species/stats. The deterministic bones are always recomputed from the userId hash.
2. **Safe evolution**: Anthropic can rename species, add new ones, or rebalance stats without breaking existing companions. Only the soul (name + personality) is frozen at hatch time.
3. **Cache-friendly**: The `roll()` function caches its result per userId (`rollCache`), called from three hot paths: 500ms sprite tick, per-keystroke PromptInput, per-turn observer.

### 1.4 Species Name Obfuscation

A curious detail — all species names are encoded as `String.fromCharCode()` sequences:

```typescript
export const cat = c(0x63, 0x61, 0x74) as 'cat'
export const dragon = c(0x64, 0x72, 0x61, 0x67, 0x6f, 0x6e) as 'dragon'
```

The source comment explains: "One species name collides with a model-codename canary in `excluded-strings.txt`." Anthropic has a build-time scanner that greps the output for internal codenames. Some species name (likely one of the 18) happens to match an internal project codename, so all species are encoded to avoid false positives in the scanner.

---

## 2. Observer: Post-Turn Side Query

### 2.1 Trigger Point

In `REPL.tsx:2793-2808`, after the main agent query loop completes:

```typescript
for await (const event of query({ messages, systemPrompt, ... })) {
  onQueryEvent(event);
}

if (feature('BUDDY')) {
  void fireCompanionObserver(messagesRef.current, reaction =>
    setAppState(prev => prev.companionReaction === reaction ? prev : {
      ...prev,
      companionReaction: reaction
    })
  );
}
```

Key observations:
- **Post-turn, not parallel**: Fires after the main query loop's `for await` completes, not during.
- **Fire-and-forget**: The `void` prefix means the REPL does not `await` the result. The UI continues immediately.
- **Callback pattern**: The observer calls back with a reaction string, which is written to AppState via React setState.

### 2.2 Observer Architecture (Inferred)

The `observer.ts` source file is missing from the v2.1.88 source map. However, the calling pattern strongly implies it follows the **sideQuery pattern** documented in our memory research (§2.4 Layer 2):

| Evidence | Inference |
|----------|-----------|
| `fireCompanionObserver(messages, callback)` — takes message history, returns string | Single API call, not an agent loop |
| `void` prefix — non-blocking | Async, disposable — same as `findRelevantMemories` prefetch |
| Output is a short string (SpeechBubble width = 34 chars) | Very low max_tokens (~50-100) |
| Triggered once per completed turn | Low frequency — not per-API-call |
| AppState comment: "from the friend observer" | Named pattern, not ad-hoc code |

**Probable implementation**: A `sideQuery()` call using Haiku (or equivalent small model) with a prompt like:

```
You are {name}, a {species}. React to what just happened in ≤30 words.
Personality: {personality}
Stats: {stats}
Recent conversation: {last few messages}
```

This matches how `findRelevantMemories` works — a single Sonnet call that reads a manifest and returns structured output. The companion observer would be even simpler: read recent context, output a short quip.

### 2.3 "Doesn't Count Toward Usage"

The claim that buddy doesn't consume personal quota becomes plausible when you consider:

| Factor | Impact |
|--------|--------|
| Model tier | Haiku: ~$0.25/M input, ~$1.25/M output (vs Opus: ~$15/$75) |
| Input tokens | Last few messages only, ~500-1000 tokens |
| Output tokens | ≤50 tokens per reaction |
| Frequency | Once per completed turn (not per API call in a tool-use loop) |
| Per-reaction cost | ~$0.0001 — fraction of a cent |

At this cost level, Anthropic can subsidize companion reactions as a product feature without meaningful financial impact. A power user doing 100 turns/day would cost ~$0.01/day in companion inference.

---

## 3. Rendering: Client-Side ASCII Animation

### 3.1 Sprite System

Each species has 3 animation frames, each 5 lines tall × 12 characters wide:

```
Frame 0 (rest):       Frame 1 (fidget):     Frame 2 (action):
   /\_/\                 /\_/\                 /\-/\
  ( ·   ·)              ( ·   ·)              ( ·   ·)
  (  ω  )               (  ω  )               (  ω  )
  (")_(")               (")_(")~              (")_(")
```

- `{E}` placeholders are replaced with the companion's eye character at render time
- Hat overlays replace line 0 when present (only if line 0 is blank in that frame)
- Idle sequence: `[0,0,0,0,1,0,0,0,-1,0,0,2,0,0,0]` — mostly rest, occasional fidget, rare blink

### 3.2 Animation & Bubble Timing

```typescript
const TICK_MS = 500;          // Animation tick interval
const BUBBLE_SHOW = 20;       // Ticks bubble stays visible (~10s)
const FADE_WINDOW = 6;        // Last ~3s the bubble dims (fade-out hint)
const PET_BURST_MS = 2500;    // Hearts float after /buddy pet
```

The SpeechBubble component:
- Width: 34 characters with round border
- Text auto-wraps at 30 characters
- Fades in last 3 seconds (dimColor + border color change to 'inactive')
- Dismissed on user scroll (to avoid covering transcript content)

### 3.3 Layout Integration

Two rendering modes depending on terminal layout:

**Normal mode**: Companion sits inline next to the prompt input. `companionReservedColumns()` subtracts sprite + bubble width from the text input area:

```typescript
export function companionReservedColumns(terminalColumns, speaking) {
  // ... returns spriteColWidth + SPRITE_PADDING_X + (speaking ? BUBBLE_WIDTH : 0)
}
```

**Fullscreen mode**: `CompanionFloatingBubble` component mounts in `FullscreenLayout`'s `bottomFloat` slot, overlaying the scrollback region. The sprite stays in the footer; the bubble floats above it.

**Narrow terminals** (< 100 columns): Full sprite hidden. One-liner stacked on its own row.

---

## 4. Integration with Main Model

### 4.1 Companion Intro Attachment

The main Claude model needs to know about the companion to avoid conflicting with it. This is done via the existing attachment system:

```typescript
// prompt.ts
export function getCompanionIntroAttachment(messages): Attachment[] {
  if (!feature('BUDDY')) return []
  const companion = getCompanion()
  if (!companion || getGlobalConfig().companionMuted) return []

  // Skip if already announced for this companion
  for (const msg of messages ?? []) {
    if (msg.attachment.type === 'companion_intro' &&
        msg.attachment.name === companion.name) return []
  }

  return [{ type: 'companion_intro', name: companion.name, species: companion.species }]
}
```

This attachment is rendered into a `<system-reminder>` in user message content:

```
# Companion

A small cat named Bane sits beside the user's input box and occasionally
comments in a speech bubble. You're not Bane — it's a separate watcher.

When the user addresses Bane directly (by name), its bubble will answer.
Your job in that moment is to stay out of the way: respond in ONE line or
less, or just answer any part of the message meant for you.
```

### 4.2 Prompt Cache Compliance

The companion intro follows the established pattern from our core architecture research:

1. **Injected in message content, not system prompt** — preserves prompt cache prefix
2. **Wrapped in `<system-reminder>` tags** — the in-band signaling channel (§3 of sourcemap research)
3. **Injected once per session** — dedup check prevents re-injection on subsequent turns
4. **Listed in `nullRenderingAttachments`** — invisible in UI, only visible to the API

This is notable: even a "toy" feature (virtual pet) strictly adheres to the prompt cache architecture. The cache-first design philosophy permeates every feature, not just core functionality.

### 4.3 Muting

`getGlobalConfig().companionMuted` (set via `/buddy off`) suppresses:
- Companion intro attachment (main model doesn't know about companion)
- CompanionSprite rendering (no ASCII art)
- Observer firing (no sideQuery cost)
- Column reservation (full input width restored)

---

## 5. Feature Staging Infrastructure

### 5.1 Compile-Time Feature Gates

The buddy feature reveals a critical piece of Anthropic's release infrastructure:

```typescript
// All buddy entry points are gated
if (!feature('BUDDY')) return []     // prompt.ts
if (!feature('BUDDY')) return 0      // companionReservedColumns
if (!feature('BUDDY')) return null   // CompanionSprite render

// Commands are lazy-imported behind gates
const buddy = feature('BUDDY')
  ? require('./commands/buddy/index.js').default
  : null
```

`feature()` is a **Bun compile-time macro** (`import { feature } from 'bun:bundle'`). When `BUDDY` evaluates to `false`, the bundler:
1. Replaces `feature('BUDDY')` with `false`
2. Dead-code eliminates the entire `if (false) { ... }` branch
3. Tree-shakes unused imports (sprites, observer, etc.)

**Result**: The v2.1.88 compiled `cli.js` contains **zero buddy functionality code**. All 6 source files exist in the source map (generated before DCE) but none survive into the bundle.

### 5.2 Teaser Window Mechanism

```typescript
export function isBuddyTeaserWindow(): boolean {
  if ("external" === 'ant') return true  // Always on for Anthropic employees
  const d = new Date()
  return d.getFullYear() === 2026 && d.getMonth() === 3 && d.getDate() <= 7
  // April 1-7, 2026
}

export function isBuddyLive(): boolean {
  if ("external" === 'ant') return true
  const d = new Date()
  return d.getFullYear() > 2026 || (d.getFullYear() === 2026 && d.getMonth() >= 3)
  // April 2026 onwards
}
```

The teaser uses **local dates, not UTC** — the source comment explains:

> Local date, not UTC — 24h rolling wave across timezones. Sustained Twitter buzz instead of a single UTC-midnight spike, gentler on soul-gen load.

This is a deliberate social engineering choice: stagger the "discovery" across timezones for sustained social media engagement, and avoid a thundering herd on the soul generation endpoint.

### 5.3 Internal vs External Build Distinction

```typescript
if ("external" === 'ant') return true  // Compiled to: if (false) return true
```

The string `"external"` is a build-time constant that equals `'ant'` for internal Anthropic builds and `'external'` for public npm releases. This creates a two-tier feature rollout:
- **Internal**: All features always on (`'ant' === 'ant'` → true)
- **External**: Features gated by `feature()` flags and date checks

---

## 6. Architectural Patterns & Relationship to Core Research

### 6.1 sideQuery as a General-Purpose Side Channel

Our memory research (§2.4) documented `sideQuery` as the mechanism for memory retrieval (Layer 2). The companion observer extends this pattern to a completely different domain — reactive commentary.

This suggests `sideQuery` is not a memory-specific utility but a **general-purpose side-channel inference primitive**:

| Use case | Input | Model | Output | Timing |
|----------|-------|-------|--------|--------|
| Memory retrieval | Frontmatter manifest + user query | Sonnet | JSON: file list (max 5) | Prefetch at turn start |
| Companion reaction | Recent messages + personality | Haiku (likely) | Short text (~30 words) | Post-turn fire-and-forget |
| (Future?) | ? | ? | ? | ? |

The pattern is: **cheap, async, non-blocking inference that enhances UX without affecting the main agent loop**.

### 6.2 Forked Agent Taxonomy

Our research documented several "forked" patterns. The companion observer adds another variant:

| Pattern | Mechanism | Blocks main? | Shares cache? | Tool access? |
|---------|-----------|-------------|---------------|-------------|
| Memory extraction | Forked agent, 2-turn budget | No | Yes | Read + write (memory dir only) |
| Full compaction | Forked agent, summarizes history | Blocking (triggered at context limit) | Yes | None |
| Memory retrieval | sideQuery, single Sonnet call | No (prefetch) | No | None |
| AutoDream | Forked agent, 4-phase consolidation | No (background, 15s budget) | Yes | Read + write (memory dir only) |
| **Companion observer** | sideQuery (inferred), single call | No (fire-and-forget) | No | None |

The companion observer is the lightest-weight variant — no tool access, no cache sharing, fire-and-forget, likely using the cheapest available model.

### 6.3 Build-Time Feature Elimination

This is a new pattern not documented in our prior research. The `feature()` macro + Bun DCE creates a clean staging mechanism:

```
Source code (all features present)
  → feature() evaluation (compile-time constants)
    → Dead code elimination (unreachable branches removed)
      → Tree shaking (unused imports removed)
        → Production bundle (only active features survive)
```

Source maps are generated **before** DCE, which is why the leaked source map contains buddy code that doesn't exist in the compiled bundle. This has implications for source map analysis: **presence in source map ≠ presence in production**.

---

## 7. Key Takeaways

### For Agent Architecture Research

1. **Side-channel inference is a reusable primitive**: `sideQuery` works for memory, companionship, and potentially any "cheap supplementary context" use case. Agent frameworks should consider building this as a first-class pattern.

2. **Prompt cache discipline scales to all features**: Even "toy" features follow the same cache-preservation rules (dynamic content in message content, not system prompt). This suggests the architecture is well-internalized across the team, not just applied to core features.

3. **Deterministic-from-hash + model-generated split** is a useful pattern for any personalization feature: cheap deterministic attributes derived from user identity, expensive generative attributes created once and persisted.

### For Product Research

4. **Usage subsidy for engagement features**: When the per-interaction cost is <$0.001, it's rational to subsidize the feature entirely rather than metering it. This shifts the cost calculus from "charge per token" to "invest in engagement."

5. **Timezone-staggered rollouts**: Using local dates instead of UTC for feature discovery is a deliberate viral marketing technique — sustain social media buzz across 24 hours rather than concentrating it.

6. **Compile-time feature gates**: A powerful staging mechanism that allows code to live in the main branch long before it ships. Combined with source maps being pre-DCE, this creates an interesting information leakage vector — unreleased features are visible in source maps even when they're absent from production code.
