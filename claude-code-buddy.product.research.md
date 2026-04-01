# Claude Code Buddy: Product Design Analysis

Last Updated: 2026-04-01 (updated with firsthand testing observations)

Sources:
- Source code analysis from v2.1.88 source map extraction (`src/buddy/`)
- Live observation of `/buddy` behavior during April 1 teaser window
- Technical implementation details: see [claude-code-buddy.research.md](./claude-code-buddy.research.md)

Research focus: Product design perspective — what user needs does Buddy serve, how does its interaction model work, and what design patterns does it employ to create engagement without disrupting a productivity tool.

---

## 1. Core Design Tension

Buddy faces an unusual product challenge: **embedding a social/emotional feature inside a professional productivity tool**. The companion must:
- Create emotional attachment (engagement, retention)
- Never interfere with work (productivity tool credibility)
- Cost effectively nothing (subsidized, no quota impact)
- Feel unique/personal (differentiation, social sharing)

Every design decision below reflects this tension.

---

## 2. Acquisition: Gacha-Style Discovery

### 2.1 Teaser → Discovery → Hatch

The onboarding funnel has three stages:

**Stage 1: Teaser notification** (passive discovery)

During the teaser window (April 1-7, 2026 local time), users who haven't hatched a companion see a rainbow-colored `/buddy` notification on startup:

```typescript
addNotification({
  key: 'buddy-teaser',
  jsx: <RainbowText text="/buddy" />,  // Each character a different color
  priority: 'immediate',
  timeoutMs: 15_000,  // Auto-dismiss after 15 seconds
})
```

This is a **curiosity trigger** — rainbow text in a monochrome terminal is visually dissonant enough to prompt investigation, but auto-dismisses to avoid nagging. The notification only appears if `!config.companion` (not yet hatched) AND within the teaser window.

**Stage 2: `/buddy` command** (active exploration)

The user types `/buddy`. The command handler (in `commands/buddy/`, source not extracted) presumably:
1. Computes `roll(userId)` to determine bones (species, rarity, stats, etc.)
2. Calls an API endpoint for **soul generation** — the model creates a name and personality based on the `inspirationSeed` and species
3. Saves the soul to `~/.claude/config.json` as `companion: { name, personality, hatchedAt }`
4. Renders the "hatch" reveal (species, rarity stars, name, stats)

The source comment references "soul-gen load" — Anthropic expects a thundering herd of hatch requests. The timezone-staggered teaser window (`new Date()` local, not UTC) is explicitly designed to spread this load:

> Local date, not UTC — 24h rolling wave across timezones. Sustained Twitter buzz instead of a single UTC-midnight spike, gentler on soul-gen load.

**Stage 3: Permanent presence** (ongoing)

After hatching, the companion appears in every subsequent session. No re-hatching, no randomization — the same companion persists indefinitely via config.

### 2.2 The Gacha Loop

The rarity system creates a classic gacha (loot box) experience:

| Rarity | Weight | Visual | Color | Hat? | Stat floor |
|--------|--------|--------|-------|------|-----------|
| common | 60% | ★ | gray (`inactive`) | No | 5 |
| uncommon | 25% | ★★ | green (`success`) | Yes | 15 |
| rare | 10% | ★★★ | blue (`permission`) | Yes | 25 |
| epic | 4% | ★★★★ | teal (`autoAccept`) | Yes | 35 |
| legendary | 1% | ★★★★★ | yellow (`warning`) | Yes | 50 |

Plus a **1% shiny chance** (orthogonal to rarity) — so a shiny legendary is 0.01%.

**Key design choice**: You get ONE companion per account. No re-rolling. This creates:
- **Scarcity** — your rarity is permanent, making rare/epic/legendary genuinely rare
- **Identity** — "my companion" rather than "a companion I chose"
- **Social comparison** — "I got a shiny legendary dragon" becomes a social flex
- **No pay-to-win** — rarity is deterministic from userId, not purchasable

The deterministic-from-hash design means your companion is pre-determined before you ever type `/buddy`. The hatch is a **reveal**, not a roll. This eliminates reroll exploits while preserving the psychological excitement of discovery.

---

## 3. Identity System

### 3.1 Visual Identity (Bones)

Each companion is uniquely characterized by the combination of:

- **Species** (18): duck, goose, blob, cat, dragon, octopus, owl, penguin, turtle, snail, ghost, axolotl, capybara, cactus, robot, rabbit, mushroom, chonk
- **Eyes** (6): `·`, `✦`, `×`, `◉`, `@`, `°`
- **Hat** (8, for uncommon+): none, crown, tophat, propeller, halo, wizard, beanie, tinyduck
- **Shiny** (1% boolean): presumably a visual modifier (sparkle effect?)

Total visual combinations: 18 × 6 × 8 × 2 = **1,728** unique appearances (for non-common; common skips hats → 18 × 6 × 2 = 216).

### 3.2 Character Identity (Soul)

The model-generated soul includes:
- **Name**: Short, distinctive (e.g., "Bane" for a cat)
- **Personality**: A text description that guides the observer's commentary style

The `inspirationSeed` (a deterministic random number from the userId PRNG) is passed to soul generation, ensuring creative variety — two users with the same species still get different names/personalities, but the same user always gets the same result.

### 3.3 Stats as Personality Flavor

Five stats shape the companion's "character":

| Stat | High = | Low = |
|------|--------|-------|
| DEBUGGING | Notices code issues, comments on errors | Oblivious to bugs |
| PATIENCE | Calm during long operations | Antsy, fidgety |
| CHAOS | Chaotic energy, unexpected comments | Predictable, steady |
| WISDOM | Insightful observations | Naive reactions |
| SNARK | Snarky, sarcastic | Sweet, earnest |

Each companion has **one peak stat** (+50-80 above floor) and **one dump stat** (-10 to +5 from floor). This guarantees every companion has a distinctive personality axis — not a flat "all-medium" blob.

Example: A high-SNARK, low-PATIENCE cat would be sarcastic and fidgety — commenting snarkily when a long build runs. A high-WISDOM, low-CHAOS owl would be calm and insightful.

**Product purpose of stats**: They serve no mechanical function — they're pure personality differentiation. But they give users something to discover, compare, and identify with. "My companion is max CHAOS" becomes part of the identity narrative.

---

## 4. Presence: Ambient Companionship

### 4.1 Spatial Layout

The companion occupies a fixed position in the terminal layout:

**Wide terminal (≥100 cols):**
```
┌─────────────────────────────────────────────────────┐
│ [conversation scrollback]                           │
│                                                     │
│                               ┌────────────────────┐│
│                               │ "nice refactor!"   ││
│                               └──────────────────┐ ││
│                                                   │ ││
│                                  /\_/\            │ ││
│                                 ( ·   ·)          ──││
│                                 (  ω  )             ││
│                                 (")_(")             ││
│                                   Bane              ││
├─────────────────────────────────────────────────────┤
│ > [user input area]                                 │
└─────────────────────────────────────────────────────┘
```

The companion sits to the **right of the input area**. `companionReservedColumns()` subtracts the sprite width from the input area, so text wrapping remains correct. When the companion speaks, an additional `BUBBLE_WIDTH = 36` chars are reserved.

**Narrow terminal (<100 cols):**
```
┌──────────────────────────┐
│ [conversation scrollback]│
│                          │
│ (·ω·) Bane              │  ← Collapsed to one-line face + name
├──────────────────────────┤
│ > [user input area]      │
└──────────────────────────┘
```

The sprite collapses to `renderFace()` — a single-line ASCII face. When speaking, the quip replaces the name (truncated to 24 chars).

**Fullscreen mode**: The bubble floats over the scrollback via `CompanionFloatingBubble` (absolute-positioned in FullscreenLayout's `bottomFloat` slot), while the sprite stays in the footer. This avoids the overflowY:hidden clip that would cut off a tall bubble.

### 4.2 Visibility Rules

The companion is hidden when it would interfere with UI:

```typescript
const companionVisible = !toolJSX?.shouldHidePromptInput  // Active tool dialog
  && !focusedInputDialog                                   // Modal dialog open
  && !showBashesDialog;                                    // Bash permission dialog
```

This is the **non-intrusion principle**: any time the user needs to interact with a dialog, the companion disappears. It never competes for attention with actionable UI.

### 4.3 Idle Animation

The companion fidgets on a 500ms tick cycle:

```typescript
const IDLE_SEQUENCE = [0, 0, 0, 0, 1, 0, 0, 0, -1, 0, 0, 2, 0, 0, 0];
//                     rest rest rest rest fidget rest rest rest blink rest rest action rest rest rest
```

15-step cycle = 7.5 seconds. Breakdown:
- **60% rest** (frame 0) — mostly still
- **7% fidget** (frame 1) — small movement (tail wag, ear twitch)
- **7% blink** (-1 → frame 0 with eyes replaced by `-`) — humanizing detail
- **7% action** (frame 2) — species-specific animation (smoke puff for dragon, bubble for octopus)

This creates a subtle "alive" feeling without being distracting. The animation is slow enough to notice peripherally but never demands attention.

**During reactions or petting**: The idle sequence is bypassed and all frames cycle rapidly (`tick % frameCount`), creating an "excited" animation.

### 4.4 Footer Focus Navigation

The companion is keyboard-navigable via footer selection:

```typescript
const focused = useAppState(s => s.footerSelection === 'companion');
```

When focused (arrow-right from tasks pill):
- Name renders in **inverse text** with spaces (` Bane `) — standard terminal "selected" affordance
- Name is **bold** and colored by rarity

This integration into the footer navigation system means the companion is a first-class UI element, not a floating overlay — it participates in the terminal's focus model.

---

## 5. Reactive Commentary: The Observer

### 5.1 Trigger Timing

The companion speaks in response to conversation events. Based on the source code:

```typescript
// REPL.tsx:2793-2808 — fires AFTER the main query loop completes
for await (const event of query({ messages, ... })) {
  onQueryEvent(event);
}
if (feature('BUDDY')) {
  void fireCompanionObserver(messagesRef.current, reaction => ...);
}
```

**When it fires**: After the entire agent turn completes (all tool use loops finished, final response rendered). Not during streaming, not during tool execution.

**When it doesn't fire**: During tool-use loops (the `for await` is still running), during the user's input time, during compaction, during background operations.

**Product implication**: The companion comments on **completed actions**, not in-progress work. This is critical for the non-intrusion principle — it never interrupts a thought in progress.

### 5.2 Reaction Content

The reaction is a short text string (max ~30 words, fitting in a 34-char-wide bubble with word wrapping). Based on the observer design (see [claude-code-buddy.research.md](./claude-code-buddy.research.md) §2.2), it's likely generated with:

- **Input**: Recent messages (what just happened), companion personality, stats
- **Model**: Haiku or equivalent (cheap, fast)
- **Constraint**: Very short output (max_tokens ~50-100)

The stats likely influence commentary style:
- High SNARK → sarcastic quips about code quality
- High DEBUGGING → notices when an error was fixed
- High CHAOS → unexpected tangential reactions
- High WISDOM → insightful observations about the approach
- High PATIENCE → calm acknowledgments of long operations

### 5.3 Bubble Lifecycle

```
[Reaction arrives] → Bubble appears (full color, italic text)
                     ↓ ~7 seconds
                     Bubble starts fading (dim color, border goes inactive)
                     ↓ ~3 seconds
                     Bubble disappears (companionReaction = undefined)
```

Total visibility: ~10 seconds. The fade-out is a **departure hint** — the user learns that bubbles are transient and doesn't need to rush to read them.

**Dismissal**: Scrolling the transcript dismisses the bubble immediately. This respects the user's intent — if they're scrolling to read something, the bubble is in the way.

### 5.4 Not Every Turn

The observer fires `void` (fire-and-forget), meaning the UI doesn't wait for it. If the observer decides the current turn doesn't warrant commentary (e.g., a trivial file read), it can simply not call the callback. The companion stays silent.

This is important: **the companion doesn't comment on everything**. It has editorial discretion. Too-frequent commentary would become noise; too-rare would feel dead. The observer's prompt likely includes guidance on when to speak vs. stay quiet.

---

## 6. Interaction Surface

### 6.1 Direct Commands

| Command | Effect | Mechanism |
|---------|--------|-----------|
| `/buddy` | First use: hatch. Subsequent: show stats/info card | `commands/buddy/index.ts` (not extracted) |
| `/buddy pet` | Hearts animation for 2.5s | Sets `companionPetAt` in AppState |
| `/buddy off` | Mute companion (no reactions, no sprite) | Sets `companionMuted` in config |

The `/buddy pet` interaction is purely emotional — it has no functional effect. The 2.5-second heart burst:

```typescript
const PET_BURST_MS = 2500;
const H = figures.heart;
const PET_HEARTS = [
  `   ${H}    ${H}   `,    // Frame 0: hearts scattered
  `  ${H}  ${H}   ${H}  `, // Frame 1: hearts rising
  ` ${H}   ${H}  ${H}   `, // Frame 2: hearts floating up
  `${H}  ${H}      ${H} `, // Frame 3: hearts dispersing
  '·    ·   ·  '           // Frame 4: sparkle fade-out
];
```

Hearts prepend above the sprite, float upward over 5 frames (~2.5s), then fade to sparkles. During petting, the idle animation switches to excited (rapid frame cycling).

### 6.2 Name-Based Address

When the user mentions the companion by name in their message, the main model is instructed to defer:

> When the user addresses Bane directly (by name), its bubble will answer. Your job in that moment is to stay out of the way: respond in ONE line or less, or just answer any part of the message meant for you.

This creates a **conversational handoff** — the user can "talk to" their companion, and the main model gracefully steps back. The companion's response comes via the observer (speech bubble), not the main model's text output.

### 6.3 Muting

`/buddy off` sets `companionMuted: true` in global config. This completely suppresses:
- Sprite rendering → `return null`
- Observer firing → no sideQuery cost
- Column reservation → full input width
- Companion intro attachment → main model doesn't know about companion

Muting is persistent (saved to config) and reversible. It's the user's escape hatch if the companion becomes annoying.

---

## 7. Engagement Psychology

### 7.1 Gacha Mechanics Without Monetization

The rarity/shiny system creates a gacha-like dopamine loop:
- **Anticipation**: Rainbow teaser → what will I get?
- **Reveal**: Species + rarity + name reveal
- **Comparison**: Social sharing of rare companions
- **Identification**: "My companion is a shiny epic axolotl named Zephyr"

But unlike commercial gacha, there's **no monetization** — no re-rolls, no premium currency, no paid upgrades. The engagement value is pure — it drives product attachment and social word-of-mouth without extracting money.

### 7.2 Parasocial Bond Formation

Several design elements encourage emotional attachment:
- **Named**: Not "the companion" but "Bane" — a named entity
- **Personality**: Consistent character across sessions
- **Petting**: Physical affection metaphor (hearts!)
- **Always present**: Visible in every session, like a desk toy
- **Reactive**: Comments on your work — feels aware of you
- **Dismissible**: Respects your autonomy — can be muted, bubbles auto-dismiss

The key balance: **enough personality to bond with, enough restraint to not annoy**.

### 7.3 Social Sharing Potential

ASCII art companions are inherently screenshot-friendly:
- Unique visual (species + eyes + hat + name)
- Rarity stars create status hierarchy
- Terminal aesthetic fits developer culture
- Stats provide conversation fodder ("my companion has 95 CHAOS")
- The "what did you get?" question drives organic sharing

The timezone-staggered rollout maximizes this: as users in earlier timezones share their companions, users in later timezones see the buzz and are primed for their own reveal.

### 7.4 The Emotional Utility of a Coding Companion

Beyond engagement metrics, the companion serves a real emotional function:

**Coding is lonely work.** Especially with AI pair programming, sessions can be long, silent, and intensely focused. A small ASCII creature that occasionally comments "nice refactor!" or fidgets beside your input provides:

- **Social presence**: Not alone in the terminal
- **Acknowledgment**: Someone (something) noticed what you did
- **Comic relief**: A snarky quip breaks tension during debugging
- **Comfort**: The pet interaction is deliberately low-stakes and warm

This is the same product insight behind GitHub's Octocat, Slack's loading messages, and Discord's Wumpus — personality in productivity tools creates emotional loyalty.

---

## 8. Design Principles Summary

| Principle | Implementation |
|-----------|---------------|
| **Never block work** | Post-turn only, auto-dismiss, hide during dialogs, dismiss on scroll |
| **Cost nothing** | Haiku sideQuery, subsidized, no quota impact |
| **Feel unique** | 1,728+ visual combinations, model-generated name/personality, deterministic-from-userId |
| **Respect autonomy** | Mutable, bubble fades, main model defers when companion speaks |
| **Reward discovery** | Rainbow teaser, gacha-style reveal, rarity hierarchy |
| **Create social value** | ASCII art aesthetics, rarity status, shareable screenshots |
| **Be alive, not loud** | 7.5s idle cycle, mostly rest, occasional fidget/blink |
| **Integrate, don't overlay** | Footer focus navigation, column reservation, layout-aware rendering |

---

## 9. Comparison with Other "Companion" Features in Dev Tools

| Aspect | Claude Code Buddy | GitHub Copilot Chat | Cursor AI | VS Code Pets |
|--------|------------------|--------------------|-----------| ------------|
| **Form** | ASCII art in terminal | Chat panel avatar | No companion | Pixel art in editor |
| **Reactivity** | Comments on work via LLM | None | None | Chases cursor |
| **Personality** | Model-generated, stat-driven | Fixed | None | Fixed species |
| **Identity** | Gacha (rarity, name, stats) | None | None | User-chosen species |
| **Cost** | Subsidized LLM inference | None | None | Zero (client-side only) |
| **Integration** | System prompt, layout reservation | N/A | N/A | Editor viewport only |

Claude Code Buddy is unique in using **LLM inference for reactive personality**. VS Code Pets is purely visual (no commentary). Copilot Chat has a personality but it's the main assistant, not a separate companion. Buddy is the first developer tool companion that is both **separate from the main AI** and **powered by its own LLM**.

---

## 10. Firsthand Observation (April 1, 2026 Teaser Window)

Tested by the author on the first day of the teaser window. Terminal width ~80 cols (narrow mode).

### What works

| Feature | Observed behavior |
|---------|-------------------|
| Presence | Small cat face in bottom-right corner (narrow mode: `(·ω·) Bane`) |
| `/buddy pet` | Returns "petted Bane" + companion speaks a short response in bubble + hearts appear |
| `/buddy off` | Mutes the companion ("companion muted") |
| Companion intro | Main model receives `<system-reminder>` with companion description |

### What does NOT work (or is not yet enabled)

| Feature | Expected (from source code) | Actual |
|---------|----------------------------|--------|
| Observer reactions | Speech bubble after each agent turn | **Never triggered** — no automatic commentary observed across an entire session |
| Full sprite (5-line ASCII art) | Visible at ≥100 col terminal width | Not tested at wide width; narrow mode shows only face |
| Hearts animation (multi-frame) | 5-frame hearts floating above sprite | Only visible as single ♥ icon in narrow mode |

### Interpretation

The teaser window (April 1-7) appears to ship **basic presence + command interactions only**. The `fireCompanionObserver` call site exists in the source, but the observer either:
1. Is not yet implemented in the current build (observer.ts was missing from v2.1.88 source map)
2. Is gated behind an additional feature flag not yet enabled
3. Deliberately deferred to the May 2026 full launch

This aligns with the internet search finding that **no one has reported seeing automatic observer reactions** — all community discussion is based on source code analysis, not live behavior.

The `/buddy pet` speech response is likely a **hardcoded reaction** from the command handler (sets both `companionPetAt` for hearts and `companionReaction` for the bubble), not an observer-driven contextual comment.

---

## 11. Open Questions

1. **Observer prompt**: What exactly does the companion see? Full message history or a summary? How does it decide when to stay silent?
2. **Soul generation**: What model generates the name/personality? How much of the `inspirationSeed` + stats influence the prompt?
3. **Stat effects on observer**: Are stats mechanically wired into the observer prompt (e.g., "your SNARK stat is 85, be very sarcastic"), or are they just part of the personality description?
4. **Engagement metrics**: Does Anthropic track companion-related metrics (pet frequency, mute rate, time-to-hatch)?
5. **Future evolution**: Will companions gain abilities? Trade between users? Evolve over time? The stats system hints at potential mechanical depth that currently serves only flavor.
6. **Multi-session continuity**: Does the observer remember previous sessions' commentary, or is each turn independent?
