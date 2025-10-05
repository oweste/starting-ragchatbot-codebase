# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Retrieval-Augmented Generation (RAG) system** for querying course materials. It's a full-stack application combining FastAPI backend with vanilla JavaScript frontend, using ChromaDB for vector storage and Anthropic's Claude for AI-powered responses with tool calling.

## Development Commands

### Setup
```bash
# Install dependencies
uv sync

# Create .env file with:
ANTHROPIC_API_KEY=your_key_here
```

### Running the Application
```bash
# Recommended: Use the run script
./run.sh

# Manual: Start FastAPI server (run from project root)
cd backend && uv run uvicorn app:app --reload --port 8000
```

Access at:
- Web UI: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Package Management
```bash
# Add new dependency
uv add <package-name>

# Update dependencies
uv sync
```

### Code Quality Tools

This project uses industry-standard code quality tools:

**Tools**:
- **black**: Automatic code formatting (line length: 88)
- **isort**: Import statement sorting (black-compatible profile)
- **flake8**: Linting and style checking

**Development Scripts** (in `scripts/` directory):

```bash
# Format code (auto-fixes issues)
./scripts/format.sh      # Linux/Mac
scripts\format.bat       # Windows

# Run linting only
./scripts/lint.sh        # Linux/Mac
scripts\lint.bat         # Windows

# Run all quality checks (check-only mode)
./scripts/quality-check.sh      # Linux/Mac
scripts\quality-check.bat       # Windows
```

**Manual Commands**:
```bash
# Format with black
uv run black backend/

# Sort imports
uv run isort backend/

# Lint with flake8
uv run flake8 backend/

# Check without modifying
uv run black --check backend/
uv run isort --check-only backend/
```

**Configuration**:
- Black & isort settings in `pyproject.toml`
- Flake8 settings in `.flake8`
- All tools configured to work together (88-char line length, compatible ignore rules)

## Architecture

### Core Pipeline Flow

**User Query → FastAPI → RAG System → AI Generator → Claude API (with tools) → Vector Store → ChromaDB**

The system uses **agentic tool calling**: Claude autonomously decides whether to search course content or answer directly from its knowledge.

### Key Components

**Backend Structure** (`backend/`):

1. **app.py** - FastAPI entry point
   - Endpoints: `/api/query`, `/api/courses`
   - Auto-loads documents from `docs/` folder on startup
   - Serves frontend static files

2. **rag_system.py** - Main orchestrator
   - Coordinates document processing, vector storage, AI generation, and session management
   - Entry point for queries: `query(query, session_id)`

3. **ai_generator.py** - Claude API integration
   - Implements tool calling workflow (two-pass: tool decision → tool execution → final response)
   - System prompt at `AIGenerator.SYSTEM_PROMPT` controls Claude's behavior
   - Temperature=0 for consistent responses

4. **vector_store.py** - ChromaDB wrapper
   - **Two collections**:
     - `course_catalog`: Course metadata for fuzzy name matching
     - `course_content`: Text chunks with embeddings for semantic search
   - Uses `all-MiniLM-L6-v2` for embeddings (configured in `config.py`)
   - `search()` method handles course name resolution + content filtering

5. **document_processor.py** - Document parsing
   - Expected format: 3-line header (title/link/instructor) + lessons
   - Sentence-based chunking with overlap (preserves context)
   - Adds contextual prefixes: `"Course {title} Lesson {num} content: {chunk}"`

6. **search_tools.py** - Tool definitions for Claude
   - `CourseSearchTool`: Defines the tool schema and execution logic
   - `ToolManager`: Routes tool calls and tracks sources
   - Tools use Anthropic's tool calling format

7. **session_manager.py** - Conversation history
   - In-memory storage (per-session message history)
   - Configurable history limit via `MAX_HISTORY` in config
   - Automatically truncates old messages

8. **config.py** - Centralized configuration
   - Key settings: `CHUNK_SIZE=800`, `CHUNK_OVERLAP=100`, `MAX_RESULTS=5`
   - Model: `claude-sonnet-4-20250514`

9. **models.py** - Data models
   - `Course`, `Lesson`, `CourseChunk` (Pydantic models)

**Frontend** (`frontend/`):
- Vanilla JS with marked.js for markdown rendering
- `script.js`: Handles API calls, chat UI, session management
- No build step required

### Document Format

Course documents in `docs/` must follow this structure:

```
Course Title: [Title]
Course Link: [URL]
Course Instructor: [Name]

Lesson 0: [Lesson Title]
Lesson Link: [URL]
[Lesson content...]

Lesson 1: [Lesson Title]
Lesson Link: [URL]
[Lesson content...]
```

Supported file types: `.txt`, `.pdf`, `.docx`

### Vector Storage Details

**ChromaDB Collections**:

1. **course_catalog** - Enables fuzzy course name matching
   - Documents: Course titles
   - Metadata: title, instructor, course_link, lessons_json, lesson_count
   - IDs: Course title (used for deduplication)

2. **course_content** - Stores chunked content
   - Documents: Text chunks with context prefixes
   - Metadata: course_title, lesson_number, chunk_index
   - IDs: `{course_title}_{chunk_index}`

**Search Strategy**:
1. User provides partial course name (e.g., "MCP")
2. Vector search on `course_catalog` finds best match (e.g., "Building Toward Computer Use with Anthropic")
3. Build filter: `{"course_title": "...", "lesson_number": N}`
4. Semantic search on `course_content` with filters
5. Return top N chunks with metadata

### Tool Calling Workflow

Claude has access to `search_course_content` tool with parameters:
- `query` (required): What to search for
- `course_name` (optional): Course title (supports partial matches)
- `lesson_number` (optional): Specific lesson to search

**Execution Flow**:
1. Claude API call with `tool_choice: auto`
2. If `stop_reason == "tool_use"`: Extract tool params → Execute via ToolManager → Return results to Claude
3. Claude synthesizes final answer from tool results
4. Sources tracked separately and returned to frontend

### Session Management

- Sessions created on first query (if no `session_id` provided)
- History format: `"User: {msg}\nAssistant: {msg}"`
- History injected into system prompt for context
- In-memory only (resets on server restart)

## Configuration

Key parameters in `backend/config.py`:
- `CHUNK_SIZE=800` - Characters per chunk
- `CHUNK_OVERLAP=100` - Overlap between chunks
- `MAX_RESULTS=5` - Search results returned
- `MAX_HISTORY=2` - Conversation exchanges to remember (2 = 4 messages)
- `EMBEDDING_MODEL="all-MiniLM-L6-v2"` - Sentence transformer model
- `ANTHROPIC_MODEL="claude-sonnet-4-20250514"`

ChromaDB stored in: `backend/chroma_db/`

## Important Design Decisions

1. **Agentic Tool Use**: Claude decides autonomously when to search vs. use existing knowledge (controlled by system prompt)

2. **Two-Collection Design**: Separating catalog from content enables fuzzy course name matching without polluting content search

3. **Context Prefixes**: Each chunk includes course/lesson info for better retrieval quality

4. **Sentence-Based Chunking**: Preserves semantic meaning better than fixed-size character chunks

5. **Stateless Tools**: Tools don't maintain state between calls; sources tracked via `last_sources` pattern

6. **No Authentication**: Currently a single-user local application

## Adding New Tools

To add a new tool for Claude:

1. Create tool class inheriting from `Tool` in `search_tools.py`
2. Implement `get_tool_definition()` and `execute()`
3. Register in `RAGSystem.__init__()`:
   ```python
   new_tool = MyNewTool(dependencies)
   self.tool_manager.register_tool(new_tool)
   ```
4. Update system prompt in `ai_generator.py` if needed

## Debugging Tips

- Check `backend/chroma_db/` to see if documents loaded
- Use `/api/courses` endpoint to verify course catalog
- API docs at `/docs` show request/response schemas
- Frontend console logs API responses
- Claude's tool decisions visible in API responses (check `stop_reason`)
- # always use uv to run the server do not use pip directl
- always use uv to run the server do not use pip directly
- use uv to run Python files