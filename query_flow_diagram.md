# RAG System Query Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                 FRONTEND                                     │
│                              (script.js)                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ 1. User types query
                                     │    "What is RAG?"
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │  POST /api/query     │
                          │  {                   │
                          │    query: "...",     │
                          │    session_id: "..." │
                          │  }                   │
                          └──────────────────────┘
                                     │
                                     │
┌─────────────────────────────────────────────────────────────────────────────┐
│                                 BACKEND                                      │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                        FastAPI (app.py)                            │    │
│  │  2. Receive request                                                │    │
│  │  3. Create/retrieve session_id                                     │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                     │                                        │
│                                     ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                      RAG System (rag_system.py)                    │    │
│  │  4. Get conversation history from SessionManager                   │    │
│  │  5. Call AI Generator with tools                                   │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                     │                                        │
│                                     ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                   AI Generator (ai_generator.py)                   │    │
│  │  6. Build system prompt + history                                  │    │
│  │  7. Call Claude API with tools                                     │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                     │                                        │
│                                     │                                        │
│                    ┌────────────────┴────────────────┐                      │
│                    │                                  │                      │
│                    ▼                                  ▼                      │
│        ┌─────────────────────┐          ┌──────────────────────┐           │
│        │  Claude decides:    │          │  Claude decides:     │           │
│        │  "I know this,      │          │  "I need to search   │           │
│        │   no search needed" │          │   course content"    │           │
│        └─────────────────────┘          └──────────────────────┘           │
│                    │                                  │                      │
│                    │                                  ▼                      │
│                    │                  ┌─────────────────────────────────┐   │
│                    │                  │  8. Tool Execution Loop         │   │
│                    │                  │  (ai_generator.py)              │   │
│                    │                  │  - Extract tool params          │   │
│                    │                  │  - Call tool_manager.execute()  │   │
│                    │                  └─────────────────────────────────┘   │
│                    │                                  │                      │
│                    │                                  ▼                      │
│                    │                  ┌─────────────────────────────────┐   │
│                    │                  │  9. CourseSearchTool            │   │
│                    │                  │  (search_tools.py)              │   │
│                    │                  │  execute(query, course, lesson) │   │
│                    │                  └─────────────────────────────────┘   │
│                    │                                  │                      │
│                    │                                  ▼                      │
│                    │                  ┌─────────────────────────────────┐   │
│                    │                  │  10. Vector Store               │   │
│                    │                  │  (vector_store.py)              │   │
│                    │                  │                                 │   │
│                    │                  │  a) Resolve course name         │   │
│                    │                  │     ┌──────────────────┐        │   │
│                    │                  │     │ course_catalog   │        │   │
│                    │                  │     │ (metadata)       │        │   │
│                    │                  │     └──────────────────┘        │   │
│                    │                  │           │                     │   │
│                    │                  │           ▼                     │   │
│                    │                  │  b) Build filters               │   │
│                    │                  │     (course + lesson)           │   │
│                    │                  │           │                     │   │
│                    │                  │           ▼                     │   │
│                    │                  │  c) Semantic search             │   │
│                    │                  │     ┌──────────────────┐        │   │
│                    │                  │     │ course_content   │        │   │
│                    │                  │     │ (chunks + embed) │        │   │
│                    │                  │     └──────────────────┘        │   │
│                    │                  │           │                     │   │
│                    │                  │           ▼                     │   │
│                    │                  │  d) Return top N results        │   │
│                    │                  └─────────────────────────────────┘   │
│                    │                                  │                      │
│                    │                                  ▼                      │
│                    │                  ┌─────────────────────────────────┐   │
│                    │                  │  11. Format Results             │   │
│                    │                  │  "[Course - Lesson N]           │   │
│                    │                  │   Content chunk..."             │   │
│                    │                  │  Store sources                  │   │
│                    │                  └─────────────────────────────────┘   │
│                    │                                  │                      │
│                    │                                  ▼                      │
│                    │                  ┌─────────────────────────────────┐   │
│                    │                  │  12. Return to AI Generator     │   │
│                    │                  │  Send tool results to Claude    │   │
│                    │                  └─────────────────────────────────┘   │
│                    │                                  │                      │
│                    │                                  ▼                      │
│                    │                  ┌─────────────────────────────────┐   │
│                    │                  │  13. Claude synthesizes answer  │   │
│                    │                  │  from search results            │   │
│                    │                  └─────────────────────────────────┘   │
│                    │                                  │                      │
│                    └──────────────────┬───────────────┘                      │
│                                       │                                      │
│                                       ▼                                      │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                      RAG System (rag_system.py)                    │    │
│  │  14. Extract sources from tool_manager                             │    │
│  │  15. Update session history                                        │    │
│  │  16. Return (response, sources)                                    │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                       │                                      │
│                                       ▼                                      │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                        FastAPI (app.py)                            │    │
│  │  17. Build JSON response                                           │    │
│  │  {                                                                 │    │
│  │    answer: "RAG is...",                                            │    │
│  │    sources: ["AI Course - Lesson 2", ...],                         │    │
│  │    session_id: "abc123"                                            │    │
│  │  }                                                                 │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                       │                                      │
└───────────────────────────────────────┼──────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                 FRONTEND                                     │
│                              (script.js)                                     │
│                                                                              │
│  18. Parse markdown response                                                │
│  19. Display answer in chat bubble                                          │
│  20. Show sources in collapsible section                                    │
│  21. Update currentSessionId                                                │
└─────────────────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
                              KEY COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│  ChromaDB        │       │  Claude API      │       │  Session Manager │
│  Collections:    │       │                  │       │                  │
│  • course_catalog│       │  • Tool calling  │       │  • Conversation  │
│  • course_content│       │  • Synthesis     │       │    history       │
└──────────────────┘       └──────────────────┘       └──────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                         DATA FLOW SUMMARY                                 │
│                                                                           │
│  Query → FastAPI → RAG System → AI Generator → Claude API                │
│                                       ↓                                   │
│                         (Claude decides to use tool)                      │
│                                       ↓                                   │
│         Tool Manager → Search Tool → Vector Store → ChromaDB             │
│                                       ↓                                   │
│                    (Results returned to Claude)                           │
│                                       ↓                                   │
│         Claude → AI Generator → RAG System → FastAPI → Frontend          │
└──────────────────────────────────────────────────────────────────────────┘
```

## Flow Characteristics

**Agentic Behavior**: Claude autonomously decides whether to search or answer directly

**Two-Pass AI Call**:
- First call: Claude decides if/what to search
- Second call: Claude synthesizes answer from tool results

**Vector Search Strategy**:
1. Fuzzy course name matching via `course_catalog`
2. Semantic content search via `course_content`
3. Filtered by course/lesson metadata

**Session Continuity**: Maintains context across multiple queries using session_id
