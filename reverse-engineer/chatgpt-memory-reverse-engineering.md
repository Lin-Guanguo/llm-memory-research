Source: [I Reverse Engineered ChatGPT's Memory System, and Here's What I Found!](https://manthanguptaa.in/posts/chatgpt_memory/) - Manthan

---

When I asked ChatGPT what it remembered about me, it listed 33 facts from my name and career goals to my current fitness routine. But how does it actually store and retrieve this information? And why does it feel so seamless?
After extensive experimentation, I discovered that ChatGPT’s memory system is far simpler than I expected. No vector databases. No RAG over conversation history. Instead, it uses four distinct layers: session metadata that adapts to your environment, explicit facts stored long-term, lightweight summaries of recent chats, and a sliding window of your current conversation.
This blog breaks down exactly how each layer works and why this approach might be superior to traditional retrieval systems. Everything here comes from reverse engineering ChatGPT’s behavior through conversation. OpenAI did not publish these implementation details.

## ChatGPT’s Context Structure

Before understanding memory, it’s important to understand the entire context ChatGPT receives for every message. The structure looks like this:

```
[0] System Instructions
[1] Developer Instructions
[2] Session Metadata (ephemeral)
[3] User Memory (long-term facts)
[4] Recent Conversations Summary (past chats, titles + snippets)
[5] Current Session Messages (this chat)
[6] Your latest message

```

The first two components define high-level behavior and safety rules. They aren’t the focus of this blog. The interesting pieces begin with Session Metadata.

## Session Metadata

These details are injected once at the beginning of a session. They are not stored permanently and don’t become part of long-term memory. This block includes:
- Device type (desktop/mobile)
- Browser + user agent
- Rough location/timezone
- Subscription level
- Usage patterns and activity frequency
- Recent model usage distribution
- Screen size, dark mode status, JS enabled, etc.
An example of session metadata is:

```
Session Metadata:
- User subscription: ChatGPT Go
- Device: Desktop browser
- Browser user-agent: Chrome on macOS (Intel)
- Approximate location: India (may be VPN)
- Local time: ~16:00
- Account age: ~157 weeks
- Recent activity:
    - Active 1 day in the last 1
    - Active 5 days in the last 7
    - Active 18 days in the last 30
- Conversation patterns:
    - Average conversation depth: ~14.8 messages
    - Average user message length: ~4057 characters
    - Model usage distribution:
        * 5% gpt-5.1
        * 49% gpt-5
        * 17% gpt-4o
        * 6% gpt-5-a-t-mini
        * etc.
- Device environment:
    - JS enabled
    - Dark mode enabled
    - Screen size: 900×1440
    - Page viewport: 812×1440
    - Device pixel ratio: 2.0
- Session duration so far: ~1100 seconds

```

This information helps the model tailor responses to your environment, but none of it persists after the session ends.

## User Memory

ChatGPT has a dedicated tool for storing and deleting stable, long-term facts about the user. These are the pieces that accumulate over weeks and months to form a persistent “profile.”
In my case, the model had 33 stored facts — things like:
- My name, age
- Career goals
- Background and past roles
- Current projects
- Areas I am studying
- Fitness routine
- Personal preferences
- Long-term interests
These are not guessed; they are explicitly stored only when:
- The user says “remember this” or “store this in memory”, or
- The model detects a fact that fits OpenAI’s criteria (like your name, job title, or stated preferences) and the user implicitly agrees through conversation
These memories are injected into every future prompt as a separate block.
If you want to add or remove anything, you can simply say:
- “Store this in memory…”
- “Delete this from memory…”
Example:

```
- User's name is Manthan Gupta.
- Previously worked at Merkle Science and Qoohoo (YC W23).
- Prefers learning through a mix of videos, papers, and hands-on work.
- Built TigerDB, CricLang, Load Balancer, FitMe.
- Studying modern IR systems (LDA, BM25, hybrid, dense embeddings, FAISS, RRF, LLM reranking).

```


## Recent Conversations Summary

This part surprised me the most, because I expected ChatGPT to use some kind of RAG across past conversations. Instead, it uses a lightweight digest.
ChatGPT keeps a list of recent conversation summaries in this format:

```
1. <Timestamp>: <Chat Title>
|||| user message snippet ||||
|||| user message snippet ||||

```

Observations:
- It only summarizes my messages, not the assistant’s.
- There were around 15 summaries available.
- They act as a loose map of my recent interests, not detailed context.
This block gives ChatGPT a sense of continuity across chats without pulling in full transcripts.
Traditional RAG systems would require:
- Embedding every past message
- Running similarity searches on each query
- Pulling in full message contexts
- Higher latency and token costs
ChatGPT’s approach is simpler: pre-compute lightweight summaries and inject them directly. This trades detailed context for speed and efficiency.

## Current Session Messages

This is the normal sliding window of the present conversation. It contains the full history (not summarized) of all messages exchanged in this session.
I wasn’t able to get the exact token limit out of ChatGPT but it did confirm:
- The cap is based on token count, not number of messages
- Once the limit is reached, older messages in the current session roll off (but memory facts and conversation summaries remain)
- Everything in this block is passed verbatim to the model, maintaining full conversational context
This is what allows the assistant to reason coherently within a session.

## How It All Works Together

When you send a message to ChatGPT, here’s what happens:
- Session starts: Session metadata is injected once, giving ChatGPT context about your device, subscription, and usage patterns.
- Every message: Your stored memory facts (33 in my case) are always included, ensuring responses align with your preferences and background.
- Cross-chat awareness: The recent conversations summary provides a lightweight map of your interests without pulling in full transcripts.
- Current context: The sliding window of current session messages maintains coherence within the conversation.
- Token budget: As the session grows, older messages roll off, but your memory facts and conversation summaries remain, preserving continuity.
This layered approach means ChatGPT can feel personal and context-aware without the computational cost of searching through thousands of past messages.

## Conclusion

ChatGPT’s memory system is a multi-layered architecture that balances personalization, performance, and token efficiency. By combining ephemeral session metadata, explicit long-term facts, lightweight conversation summaries, and a sliding window of current messages, ChatGPT achieves something remarkable: it feels personal and context-aware without the computational overhead of traditional RAG systems.
The key insight here is that not everything needs to be “memory” in the traditional sense. Session metadata adapts to your environment in real-time. Explicit facts persist across sessions. Conversation summaries provide continuity without detail. And the current session maintains coherence. Together, these dynamic components—each updated as the session progresses and your preferences evolve—create the illusion of a system that truly knows you.
For users, this means ChatGPT can feel increasingly personal over time without requiring explicit knowledge base management. For developers, it’s a lesson in pragmatic engineering: sometimes simpler, more curated approaches outperform complex retrieval systems, especially when you control the entire pipeline.
The trade-off is clear: ChatGPT sacrifices detailed historical context for speed and efficiency. But for most conversations, that’s exactly the right balance. The system remembers what matters (your preferences, goals, and recent interests) while staying fast and responsive.
This blog is based on experimentation and reverse engineering through conversation, not official documentation—so take it with a grain of salt. If you found this interesting, I’d love to hear your thoughts. Share it onTwitter,LinkedIn, orPeerlist, or reach out at guptaamanthan01[at]gmail[dot]com.