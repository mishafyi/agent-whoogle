---
name: agent-whoogle
description: >
  Local Google search for AI agents. Use when you need to search the web,
  find documentation, look up APIs, verify facts, or find current information.
  Triggers on "search for", "look up", "find", "google", or when you need
  web search results. No API keys, no Docker, no server required.
license: MIT
metadata:
  author: agent-whoogle
  version: "0.1.0"
  argument-hint: <search-query>
---

# Agent Whoogle

Google search for AI agents. Runs locally, returns structured JSON, no setup needed.

Based on [Whoogle Search](https://github.com/benbusby/whoogle-search) by Ben Busby.

## When to Use

- You need to search the web for information
- You need to find documentation, APIs, or code examples
- You need to verify facts or find current information
- The user asks you to "search for", "look up", "find", or "google" something

## When NOT to Use

- You already have the information you need
- The question is about the local codebase (use Grep/Glob instead)
- You've already searched for the same thing in this session

## How to Search

Run the search script from the skill directory:

```bash
python <skill_dir>/scripts/search.py "your search query"
```

Or with `uv` (auto-installs dependencies):

```bash
uv run <skill_dir>/scripts/search.py "your search query"
```

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `--num N` | Number of results | 10 |
| `--start N` | Result offset (pagination) | 0 |
| `--lang LANG` | Search language (e.g., `lang_en`) | auto |
| `--country CC` | Country code (e.g., `US`) | auto |
| `--safe` | Enable SafeSearch | off |
| `--time RANGE` | Time filter: `hour`, `day`, `week`, `month`, `year` | none |
| `--proxy URL` | Proxy URL (e.g., `socks5://host:port`) | none |
| `--raw` | Plain text output instead of JSON | JSON |

### Examples

```bash
# Basic search
python <skill_dir>/scripts/search.py "python asyncio tutorial"

# Recent results only
python <skill_dir>/scripts/search.py --time week "latest npm security advisory"

# Paginate
python <skill_dir>/scripts/search.py --start 10 "react server components"
```

## Response Format

```json
{
  "query": "your search query",
  "results": [
    {
      "title": "Page Title",
      "url": "https://example.com/page",
      "snippet": "Brief description of the page content..."
    }
  ],
  "error": null,
  "message": null
}
```

## Error Handling

| `error` value | Exit code | Meaning | What to do |
|---------------|-----------|---------|------------|
| `null` | 0 | Success | Use the results |
| `"rate_limited"` | 2 | Google CAPTCHA or 429 | Wait and retry, or use `--proxy` |
| `"network_error"` | 1 | Connection failed | Check network, retry |
| `"missing_query"` | 1 | No query provided | Provide a search query |
| `"unexpected_error"` | 1 | Internal error | Check stderr for traceback, report bug |

## Dependencies

Requires Python 3.9+. Dependencies (`httpx`, `beautifulsoup4`, `cachetools`) are installed automatically when using `uv run`, or install manually with:

```bash
pip install httpx[http2] beautifulsoup4 cachetools
```
