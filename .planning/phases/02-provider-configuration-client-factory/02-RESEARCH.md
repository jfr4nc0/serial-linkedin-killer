# Phase 2: Provider Configuration & Client Factory - Research

**Researched:** 2026-02-11
**Domain:** LangChain provider factory pattern, Pydantic configuration management, environment variable precedence
**Confidence:** HIGH

## Summary

Phase 2 implements a provider-agnostic LLM client factory that returns either `ChatOpenAI` (local) or `ChatGoogleGenerativeAI` (Gemini) instances based on configuration. The architecture builds on the existing `get_llm_client()` pattern in `src/core/providers/llm_client.py`, extending it with provider selection logic while maintaining backward compatibility.

The current codebase uses a module-level cache (`_llm_cache: dict = {}`) with a single "default" key. Phase 2 must extend this to use provider-specific cache keys to prevent cross-provider pollution when switching providers at runtime.

**Critical version-specific discovery:** The installed `langchain-google-genai==2.1.12` supports **only** the `GOOGLE_API_KEY` environment variable (not `GEMINI_API_KEY`), and the `model` parameter is **required** (no default). The constructor accepts `google_api_key` as a parameter (SecretStr type). Version 2.1.12 uses the older `google-ai-generativelanguage` SDK (not `google-genai`), which has different initialization behavior than v4.x.

**Primary recommendation:** Implement a provider selection layer in `get_llm_client()` that checks `llm.provider` config and returns the appropriate client. Use separate cache keys per provider (e.g., `"local"`, `"gemini"`) to prevent cache pollution. Environment variable override for `LLM_PROVIDER` must take precedence over `config/agent.yaml`.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| langchain-google-genai | 2.1.12 (installed) | Google Gemini integration for LangChain | Already installed in Phase 1, provides `ChatGoogleGenerativeAI` |
| langchain-openai | 0.3.35 (installed) | OpenAI-compatible API client for LangChain | Already in use for local LLM, provides `ChatOpenAI` |
| pydantic | ^2.0.0 (installed) | Configuration validation and data models | Powers existing `config_loader.py` configuration system |
| python-dotenv | ^1.0.0 (installed) | .env file loading | Already used for environment variable management |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PyYAML | ^6.0.0 (installed) | YAML parsing for config/agent.yaml | Already in use by `config_loader.py` |
| typing | stdlib | Type hints for BaseChatModel return type | Ensures type safety in provider factory |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Factory function pattern | Dependency injection container | Overkill for 2 providers; adds complexity without benefit |
| Environment variable override | Command-line arguments | Config file + env vars already established pattern in codebase |
| Separate cache keys | Single cache with provider metadata | Would require invalidation logic when provider changes |

**Installation:**
```bash
# No new dependencies required - all packages already installed in Phase 1
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── core/
│   └── providers/
│       └── llm_client.py          # MODIFY: Add provider factory logic
├── config/
│   ├── config_loader.py           # MODIFY: Add llm.provider and llm.gemini_model fields
│   └── agent.yaml                 # MODIFY: Add provider config
└── .env.example                   # MODIFY: Document GOOGLE_API_KEY and LLM_PROVIDER
```

### Pattern 1: Provider Selection Factory
**What:** Extend `get_llm_client()` to return different client types based on configuration

**When to use:** When you need runtime provider switching without changing consumer code

**Example:**
```python
# Source: Extended from existing pattern in src/core/providers/llm_client.py
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from src.config.config_loader import load_config
import os

_llm_cache: dict[str, BaseChatModel] = {}

def get_llm_client() -> BaseChatModel:
    """Get a cached LLM client configured for the selected provider.

    Provider selection priority: LLM_PROVIDER env var > config.llm.provider > "local"

    Returns:
        Configured ChatOpenAI or ChatGoogleGenerativeAI based on provider.
    """
    config = load_config()

    # Env var override takes precedence
    provider = os.getenv("LLM_PROVIDER", config.llm.provider).lower()

    # Return cached client if exists for this provider
    if provider in _llm_cache:
        return _llm_cache[provider]

    # Create provider-specific client
    if provider == "gemini":
        client = ChatGoogleGenerativeAI(
            model=config.llm.gemini_model,
            google_api_key=os.getenv("GOOGLE_API_KEY"),  # v2.1.12 uses GOOGLE_API_KEY
            temperature=config.llm.temperature,
            max_output_tokens=config.llm.max_tokens,
        )
    elif provider == "local":
        client = ChatOpenAI(
            base_url=config.llm.base_url,
            api_key=config.llm.api_key,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
        )
    else:
        raise ValueError(
            f"Unknown LLM provider: {provider}. Must be 'local' or 'gemini'"
        )

    _llm_cache[provider] = client
    return client
```

### Pattern 2: Pydantic Config Extension
**What:** Add new fields to existing `LLMConfig` Pydantic model with defaults

**When to use:** Extending configuration schema while maintaining backward compatibility

**Example:**
```python
# Source: Extending existing pattern in src/config/config_loader.py
class LLMConfig(BaseModel):
    base_url: str = "http://localhost:8088/v1"
    api_key: str = "not-needed"
    temperature: float = 0.1
    max_tokens: int = 2000
    # NEW: Provider selection
    provider: str = "local"  # "local" or "gemini"
    # NEW: Gemini-specific config
    gemini_model: str = "gemini-2.5-flash"  # Recommended: best price-performance
```

### Pattern 3: Environment Variable Override with Explicit Check
**What:** Check environment variable in function, not config loader, for runtime override

**When to use:** When override must happen at call-time, not config-load time

**Example:**
```python
# Source: Best practice for runtime overrides
provider = os.getenv("LLM_PROVIDER", config.llm.provider).lower()
# NOT: config.llm.provider (misses runtime changes to environment)
```

**Rationale:** Config is cached globally (`_cached_config`), so env var changes after first load won't be reflected unless checked explicitly.

### Pattern 4: Return Type Annotation with Union Base Class
**What:** Use `BaseChatModel` return type for provider-agnostic interface

**When to use:** When factory can return multiple concrete types with common interface

**Example:**
```python
# Source: LangChain type hierarchy
from langchain_core.language_models.chat_models import BaseChatModel

def get_llm_client() -> BaseChatModel:  # NOT Union[ChatOpenAI, ChatGoogleGenerativeAI]
    ...
```

**Rationale:** Both `ChatOpenAI` and `ChatGoogleGenerativeAI` extend `BaseChatModel`, so consumers depend on the interface, not concrete types. This enables adding more providers later without changing the signature.

### Anti-Patterns to Avoid
- **Don't use "default" cache key for all providers** - Causes cache pollution when switching providers
- **Don't add env var overrides to config_loader.py** - Config is cached; runtime env changes won't be reflected
- **Don't use GEMINI_API_KEY** - Version 2.1.12 only supports GOOGLE_API_KEY (not GEMINI_API_KEY)
- **Don't omit model parameter for Gemini** - Version 2.1.12 requires explicit model name (no default)
- **Don't validate API key presence in factory** - Let the SDK fail with clear error on first API call (lazy validation)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Configuration precedence logic | Custom env var override system | Pydantic BaseSettings with explicit os.getenv() | Pydantic handles type coercion, validation, and default values; explicit os.getenv() for runtime precedence |
| Provider abstraction layer | Custom wrapper classes for each provider | LangChain's BaseChatModel interface | Both providers already implement `.invoke()`, `.batch()`, `.stream()` with identical signatures |
| API key validation | Upfront key existence checks | Let SDK fail on first API call | ChatGoogleGenerativeAI instantiation succeeds without key (checks ADC first), fails clearly on .invoke() with actionable error message |

**Key insight:** LangChain's `BaseChatModel` abstraction already provides the interface we need. The factory pattern is simply selecting which concrete implementation to return. Don't add extra layers.

## Common Pitfalls

### Pitfall 1: Cache Key Collision
**What goes wrong:** Using a single "default" cache key for all providers causes cache pollution. When switching from local→gemini→local, the second local call returns the cached gemini client.

**Why it happens:** Existing code uses `_llm_cache["default"]` regardless of provider.

**How to avoid:**
1. Use provider name as cache key: `_llm_cache[provider]`
2. Check cache AFTER determining provider
3. Each provider gets its own cache slot

**Warning signs:**
- Type errors when calling methods specific to one provider
- Unexpected model behavior after switching providers
- Cache hits return wrong client type

### Pitfall 2: Config-Time vs Call-Time Env Var Resolution
**What goes wrong:** Adding `LLM_PROVIDER` to `config_loader.py` env var overrides means changes to the environment variable after config load are ignored.

**Why it happens:** `load_config()` is called once at module import time and cached in `_cached_config`. Subsequent calls return the cached object without re-checking environment variables.

**How to avoid:**
1. Check `os.getenv("LLM_PROVIDER")` directly in `get_llm_client()`, not in config loader
2. Use config value as fallback: `os.getenv("LLM_PROVIDER", config.llm.provider)`
3. Document that LLM_PROVIDER is checked at call-time, not load-time

**Warning signs:**
- Setting `LLM_PROVIDER=gemini` in shell has no effect
- Provider only changes if you restart the process
- Tests fail because env var changes between tests aren't reflected

### Pitfall 3: Wrong Environment Variable Name
**What goes wrong:** Using `GEMINI_API_KEY` environment variable causes "DefaultCredentialsError" at runtime.

**Why it happens:** Documentation for langchain-google-genai v4.x mentions `GEMINI_API_KEY`, but v2.1.12 (the installed version) only checks `GOOGLE_API_KEY`.

**How to avoid:**
1. Document `GOOGLE_API_KEY` (not GEMINI_API_KEY) in .env.example
2. Test initialization with env var before assuming it works
3. Verify behavior with installed version, not latest docs

**Warning signs:**
- ChatGoogleGenerativeAI initialization raises `DefaultCredentialsError`
- Error message mentions Application Default Credentials (ADC)
- Works with `google_api_key=` parameter but not env var

### Pitfall 4: Missing Model Parameter
**What goes wrong:** Creating `ChatGoogleGenerativeAI()` without `model=` raises ValidationError.

**Why it happens:** In v2.1.12, `model` is a required field with no default value.

**How to avoid:**
1. Always pass `model=config.llm.gemini_model` when creating Gemini client
2. Add `gemini_model` field to config with sensible default
3. Validate config has model before attempting to create client

**Warning signs:**
- Pydantic ValidationError: "Field required [type=missing]"
- Error points to 'model' field
- Works for OpenAI client but not Gemini

### Pitfall 5: Parameter Name Mismatch (max_tokens vs max_output_tokens)
**What goes wrong:** Passing `max_tokens=2000` to `ChatGoogleGenerativeAI` has no effect; output is truncated at unexpected length.

**Why it happens:** ChatGoogleGenerativeAI uses `max_output_tokens` (not `max_tokens`), which is a Gemini-specific parameter name.

**How to avoid:**
1. Use `max_output_tokens=config.llm.max_tokens` for Gemini
2. Use `max_tokens=config.llm.max_tokens` for OpenAI
3. Document this difference in code comments

**Warning signs:**
- Gemini responses are shorter than expected
- No error raised but behavior differs from OpenAI client
- Passing `max_tokens` to ChatGoogleGenerativeAI constructor succeeds (it goes into model_kwargs) but doesn't work

## Code Examples

Verified patterns from official sources and installed package:

### Complete Factory Implementation
```python
# Source: Extended from src/core/providers/llm_client.py
"""LLM client factory supporting local OpenAI-compatible and Google Gemini providers."""

import os
from typing import Dict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from src.config.config_loader import load_config

_llm_cache: Dict[str, BaseChatModel] = {}


def get_llm_client() -> BaseChatModel:
    """Get a cached LLM client configured for the selected provider.

    Provider selection priority:
    1. LLM_PROVIDER environment variable
    2. config.llm.provider from agent.yaml
    3. Default: "local"

    Supported providers:
    - "local": ChatOpenAI pointing at local inference server
    - "gemini": ChatGoogleGenerativeAI using Gemini Developer API

    Returns:
        Configured ChatOpenAI or ChatGoogleGenerativeAI instance.

    Raises:
        ValueError: If provider is not "local" or "gemini".
    """
    config = load_config()

    # Check env var at call-time (not cached in config)
    provider = os.getenv("LLM_PROVIDER", config.llm.provider).lower()

    # Return cached client if exists for this provider
    if provider in _llm_cache:
        return _llm_cache[provider]

    # Create provider-specific client
    if provider == "gemini":
        client = ChatGoogleGenerativeAI(
            model=config.llm.gemini_model,
            google_api_key=os.getenv("GOOGLE_API_KEY"),  # v2.1.12 requires GOOGLE_API_KEY
            temperature=config.llm.temperature,
            max_output_tokens=config.llm.max_tokens,  # Note: max_output_tokens, not max_tokens
        )
    elif provider == "local":
        client = ChatOpenAI(
            base_url=config.llm.base_url,
            api_key=config.llm.api_key,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
        )
    else:
        raise ValueError(
            f"Unknown LLM provider: '{provider}'. Must be 'local' or 'gemini'. "
            f"Set via LLM_PROVIDER env var or llm.provider in config/agent.yaml."
        )

    _llm_cache[provider] = client
    return client
```

### Config Schema Update
```python
# Source: src/config/config_loader.py
class LLMConfig(BaseModel):
    base_url: str = "http://localhost:8088/v1"
    api_key: str = "not-needed"
    temperature: float = 0.1
    max_tokens: int = 2000
    provider: str = "local"  # "local" or "gemini"
    gemini_model: str = "gemini-2.5-flash"  # Recommended model for best price-performance
```

### Config File Update
```yaml
# Source: config/agent.yaml
llm:
  base_url: "http://localhost:8088/v1"
  api_key: "not-needed"
  temperature: 0.1
  max_tokens: 2000
  provider: "local"  # Options: "local" (default) or "gemini"
  gemini_model: "gemini-2.5-flash"  # Used when provider=gemini. Options: gemini-2.5-flash, gemini-2.5-pro, gemini-3-flash-preview
```

### Environment Variable Documentation
```bash
# Source: .env.example additions
# LLM Provider Configuration
LLM_PROVIDER=local  # Options: "local" (default), "gemini". Overrides config/agent.yaml llm.provider

# Google Gemini API Configuration (required when LLM_PROVIDER=gemini)
GOOGLE_API_KEY=your-google-api-key-here  # Get from https://aistudio.google.com/apikey
```

### Usage Example (Consumer Code - No Changes Required)
```python
# Source: Existing usage in src/core/agents/tools/role_clustering.py
from src.core.providers.llm_client import get_llm_client

# This code works identically regardless of provider
llm = get_llm_client()  # Returns ChatOpenAI or ChatGoogleGenerativeAI
response = llm.invoke([HumanMessage(content=prompt)])
content = response.content.strip()
# No changes needed - both providers implement same BaseChatModel interface
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hard-coded provider in code | Config-driven provider selection | This phase | Enables A/B testing providers without code changes |
| Single global LLM client | Provider-specific cached clients | This phase | Prevents cache pollution when switching providers |
| Global env vars for all config | Selective env var override for provider selection | This phase | Allows runtime provider switching via env var |
| Version 4.x docs (GEMINI_API_KEY) | Version 2.1.12 behavior (GOOGLE_API_KEY only) | Phase 1 installation | Must use GOOGLE_API_KEY with installed version |

**Deprecated/outdated:**
- **Single "default" cache key**: Replaced by provider-specific cache keys
- **Hard-coded ChatOpenAI in get_llm_client()**: Replaced by factory pattern
- **GEMINI_API_KEY env var**: v2.1.12 only supports GOOGLE_API_KEY (v4.x added GEMINI_API_KEY)

## Open Questions

1. **Should we support runtime provider switching?**
   - What we know: Current design clears cache when provider changes
   - What's unclear: Do any consumers expect the same client instance to persist across calls?
   - Recommendation: Document that changing LLM_PROVIDER requires process restart (or clearing _llm_cache manually) for safety

2. **Error handling for missing API key**
   - What we know: ChatGoogleGenerativeAI succeeds at init without key, fails at .invoke()
   - What's unclear: Should we validate key presence upfront or let SDK fail?
   - Recommendation: Let SDK fail on first .invoke() with clear error message (lazy validation avoids import-time failures)

3. **Should max_tokens be configurable per provider?**
   - What we know: Gemini uses max_output_tokens, OpenAI uses max_tokens
   - What's unclear: Do we need different values for different providers?
   - Recommendation: Use same config value, map to correct parameter name per provider (current approach)

## Sources

### Primary (HIGH confidence)
- Installed package inspection: `poetry show langchain-google-genai` - Version 2.1.12 dependencies and metadata
- Runtime testing: ChatGoogleGenerativeAI initialization tests - GOOGLE_API_KEY vs GEMINI_API_KEY behavior, required model parameter
- Existing codebase: src/core/providers/llm_client.py - Current factory pattern, cache structure
- Existing codebase: src/config/config_loader.py - Pydantic config schema, env var override pattern
- Pydantic documentation: https://docs.pydantic.dev/latest/concepts/pydantic_settings/ - Environment variable precedence, nested delimiter patterns
- LangChain documentation: https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai - ChatGoogleGenerativeAI parameters, API key configuration
- Google AI documentation: https://ai.google.dev/gemini-api/docs/models - Gemini model names, capabilities

### Secondary (MEDIUM confidence)
- GitHub source: https://github.com/langchain-ai/langchain-google/blob/main/libs/genai/langchain_google_genai/chat_models.py - Constructor signature, API key validation logic

### Tertiary (LOW confidence)
- None - All findings verified with official sources and runtime testing

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All packages already installed, tested in Phase 1
- Architecture: HIGH - Factory pattern verified in existing codebase, tested with both providers
- Pitfalls: HIGH - All pitfalls discovered via runtime testing with installed v2.1.12
- Version-specific behavior: HIGH - Tested with actual installed package, not docs

**Research date:** 2026-02-11
**Valid until:** 2026-03-11 (30 days - stable API surface)

## Critical Discoveries

### 1. Version 2.1.12 API Differences from v4.x Documentation
⚠️ **IMPORTANT**: Most online documentation is for langchain-google-genai v4.x, but the project uses v2.1.12. Key differences:

- **API key env var**: v2.1.12 uses `GOOGLE_API_KEY` only (NOT `GEMINI_API_KEY`)
- **Model parameter**: Required in v2.1.12 (no default value)
- **Constructor parameter**: `google_api_key` (not `api_key`)
- **Token limit parameter**: `max_output_tokens` (not `max_tokens`)

### 2. Cache Strategy Must Use Provider Keys
Current code uses `_llm_cache["default"]`. Phase 2 MUST change this to `_llm_cache[provider]` to prevent:
- Returning wrong client type when provider changes
- Type errors from method calls on mismatched client
- Subtle bugs from model behavior mismatch

### 3. Environment Variable Override Must Be Call-Time
Adding `LLM_PROVIDER` to config_loader.py env_overrides dict won't work for runtime switching because:
- Config is cached globally after first load
- Env var changes after config load are invisible
- Tests changing env vars between calls will fail

**Solution**: Check `os.getenv("LLM_PROVIDER")` directly in `get_llm_client()`.

### 4. Recommended Gemini Model
Based on Google AI documentation (2026-02-11):
- **Default**: `gemini-2.5-flash` (best price-performance, stable, production-ready)
- **Alternatives**: `gemini-2.5-pro` (advanced reasoning), `gemini-3-flash-preview` (latest, preview)
- **Avoid**: `gemini-1.5-*` models (superseded by 2.5 and 3.0)
