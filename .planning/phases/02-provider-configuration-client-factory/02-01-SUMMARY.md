---
phase: 02-provider-configuration-client-factory
plan: 01
subsystem: core/providers
tags: [configuration, llm, provider-factory, gemini]
dependency_graph:
  requires: [langchain-google-genai@2.1.12]
  provides: [multi-provider-llm-client, gemini-support]
  affects: [role-clustering, cv-analysis, agent-core]
tech_stack:
  added: [ChatGoogleGenerativeAI]
  patterns: [provider-factory, config-driven-selection, env-override]
key_files:
  created: []
  modified:
    - src/config/config_loader.py
    - config/agent.yaml
    - .env.example
    - src/core/providers/llm_client.py
decisions:
  - Use "local" as default provider for backward compatibility
  - LLM_PROVIDER env var checked at call-time (not config-load time) to avoid cache staleness
  - Provider-specific cache keys prevent cross-provider pollution
  - GEMINI_API_KEY passed explicitly to ChatGoogleGenerativeAI constructor
  - Return type changed to BaseChatModel for provider flexibility
  - Use max_output_tokens for Gemini (not max_tokens)
  - Lazy API key validation (let SDK fail on first invoke)
metrics:
  duration_seconds: 153
  completed_date: 2026-02-11
---

# Phase 02 Plan 01: Provider Configuration & Client Factory Summary

**One-liner:** Config-driven LLM provider factory supporting local OpenAI and Google Gemini with environment variable overrides.

## Objective

Implement config-driven LLM provider selection and a client factory that returns the correct provider instance (ChatOpenAI for local, ChatGoogleGenerativeAI for Gemini) based on configuration and environment variable overrides. This enables switching between local LLM and Gemini without code changes, unblocking Gemini-powered role clustering for large employee datasets.

## Tasks Completed

### Task 1: Extend config schema, YAML defaults, and env var documentation
**Commit:** 9c63112
**Files:** src/config/config_loader.py, config/agent.yaml, .env.example

- Added `provider` (default "local") and `gemini_model` (default "gemini-3-flash-preview") fields to LLMConfig
- Updated agent.yaml with new llm.provider and llm.gemini_model fields with inline comments
- Documented LLM_PROVIDER and GEMINI_API_KEY in .env.example with usage context and API key URL
- Preserved backward compatibility with existing configs (no env_overrides added per research)

**Verification:** Confirmed config loads with correct defaults, LLMConfig Pydantic validation works, YAML contains new fields, .env.example documents both variables.

### Task 2: Implement provider factory in get_llm_client()
**Commit:** ec99f84
**Files:** src/core/providers/llm_client.py

- Rewrote get_llm_client() as provider factory supporting "local" and "gemini"
- Provider resolution: LLM_PROVIDER env var > config.llm.provider > default "local"
- Returns ChatOpenAI for local provider (unchanged behavior)
- Returns ChatGoogleGenerativeAI for gemini provider with correct parameters:
  - model=config.llm.gemini_model
  - google_api_key=os.getenv("GEMINI_API_KEY")
  - max_output_tokens (not max_tokens)
- Provider-specific cache keys prevent stale clients when switching
- Raises ValueError for unknown providers with helpful message
- Changed return type from ChatOpenAI to BaseChatModel
- Updated module docstring and function docstring

**Verification:** Confirmed local provider returns ChatOpenAI, gemini provider returns ChatGoogleGenerativeAI, invalid provider raises ValueError, return type is BaseChatModel, cache isolation works, all consumers import cleanly.

## Deviations from Plan

None - plan executed exactly as written.

## Success Criteria Met

- [x] get_llm_client() returns ChatOpenAI for provider="local" with identical behavior to before
- [x] get_llm_client() returns ChatGoogleGenerativeAI for provider="gemini" with configured model and API key
- [x] LLM_PROVIDER env var overrides config file llm.provider value
- [x] Provider-specific cache keys prevent cross-provider pollution
- [x] config/agent.yaml includes provider and gemini_model fields with documented defaults
- [x] .env.example documents GEMINI_API_KEY and LLM_PROVIDER
- [x] No changes required in any consumer code (role_clustering.py, cv_analysis_tools.py, agent.py)

## Integration Points

**Consumers:**
- src/core/agent.py - Uses get_llm_client() for agent graph
- src/tools/cv_analysis_tools.py - Uses get_llm_client() for CV analysis
- src/tools/role_clustering.py - Uses get_llm_client() for role clustering (primary beneficiary)
- src/core/providers/__init__.py - Re-exports get_llm_client
- src/__init__.py - Imports from providers

**All consumers** continue working without changes because they only use `.invoke()` and `.batch()` methods which are on the BaseChatModel interface.

## Technical Details

**Configuration Schema:**
```python
class LLMConfig(BaseModel):
    provider: str = "local"  # "local" or "gemini"
    gemini_model: str = "gemini-3-flash-preview"
```

**Provider Selection Logic:**
1. Read LLM_PROVIDER env var (if set)
2. Fallback to config.llm.provider
3. Default to "local"
4. Normalize to lowercase

**Cache Strategy:**
- Key: provider name ("local" or "gemini")
- Prevents returning cached local client when gemini is requested and vice versa

**Gemini-specific handling:**
- Use `max_output_tokens` parameter (not `max_tokens`)
- Pass `google_api_key` explicitly from GEMINI_API_KEY env var
- Model is required (no default in SDK v2.1.12)

## Testing Evidence

```bash
# Default provider (backward compatibility)
$ poetry run python -c "from src.core.providers.llm_client import get_llm_client; print(type(get_llm_client()))"
<class 'langchain_openai.chat_models.base.ChatOpenAI'>

# Gemini provider
$ LLM_PROVIDER=gemini GEMINI_API_KEY=test poetry run python -c "..."
<class 'langchain_google_genai.chat_models.ChatGoogleGenerativeAI'>

# Invalid provider
$ LLM_PROVIDER=invalid poetry run python -c "..."
ValueError: Unknown LLM provider: 'invalid'. Must be 'local' or 'gemini'...
```

## Next Steps

This plan unblocks:
- **Phase 03**: Gemini integration in role clustering for large employee datasets
- **Future**: Additional providers (Anthropic, Azure OpenAI) following same pattern

No downstream changes required. Role clustering can now switch to Gemini by setting:
```bash
LLM_PROVIDER=gemini
GEMINI_API_KEY=<your-key>
```

## Self-Check: PASSED

**Created files verified:**
- No new files created (as expected)

**Modified files verified:**
```bash
$ [ -f "src/config/config_loader.py" ] && echo "FOUND: src/config/config_loader.py"
FOUND: src/config/config_loader.py

$ [ -f "config/agent.yaml" ] && echo "FOUND: config/agent.yaml"
FOUND: config/agent.yaml

$ [ -f ".env.example" ] && echo "FOUND: .env.example"
FOUND: .env.example

$ [ -f "src/core/providers/llm_client.py" ] && echo "FOUND: src/core/providers/llm_client.py"
FOUND: src/core/providers/llm_client.py
```

**Commits verified:**
```bash
$ git log --oneline --all | grep -q "9c63112" && echo "FOUND: 9c63112"
FOUND: 9c63112

$ git log --oneline --all | grep -q "ec99f84" && echo "FOUND: ec99f84"
FOUND: ec99f84
```
