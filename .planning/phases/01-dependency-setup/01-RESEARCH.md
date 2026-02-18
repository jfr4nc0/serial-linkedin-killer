# Phase 1: Dependency Setup - Research

**Researched:** 2026-02-11
**Domain:** Python dependency management with Poetry, LangChain Google Gemini integration
**Confidence:** HIGH

## Summary

Phase 1 focuses on adding `langchain-google-genai` as a Poetry dependency to enable Gemini model integration with the existing LangChain infrastructure. The package is mature (v4.2.0), actively maintained by the LangChain team, and follows the same patterns as the existing `langchain-openai` integration already in the codebase.

The current project uses Python 3.12.3 with Poetry 1.8.2, LangChain 0.3.27, and langchain-core 0.3.83. The `langchain-google-genai` package requires `langchain-core >=1.2.5,<2.0.0`, which means it's compatible with langchain-core 1.x but **not** with the currently installed 0.3.x version. This creates a **critical compatibility issue** that must be addressed.

**Primary recommendation:** Add `langchain-google-genai` with a caret constraint (`^4.0.0`) to allow patch and minor updates. However, be prepared for Poetry to upgrade langchain-core to 1.x, which may require testing all existing LangChain functionality to ensure backward compatibility.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| langchain-google-genai | 4.2.0 (latest) | Google Gemini model integration for LangChain | Official LangChain integration, maintained by LangChain team, supports all Gemini features |
| langchain-core | >=1.2.5,<2.0.0 (required) | Core LangChain abstractions | Required peer dependency for langchain-google-genai |
| google-genai | >=1.56.0,<2.0.0 | Google's unified SDK for Gemini API | Required by langchain-google-genai, replaces legacy google-ai-generativelanguage SDK |
| pydantic | >=2.0.0,<3.0.0 | Data validation | Already in project, compatible |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| filetype | >=1.2.0,<2.0.0 | File type detection | Auto-installed with langchain-google-genai, used for multimodal content |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| langchain-google-genai | google-genai (direct SDK) | Loses LangChain abstractions, manual Langfuse tracing, inconsistent interface with existing OpenAI integration |
| langchain-google-genai | langchain-google-vertexai | Requires GCP authentication, more complex setup, designed for Vertex AI not Gemini Developer API |

**Installation:**
```bash
poetry add langchain-google-genai
```

This will automatically resolve dependencies and update poetry.lock.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── core/
│   └── providers/
│       ├── llm_client.py          # Existing OpenAI client
│       └── gemini_client.py       # New Gemini client (Phase 2)
├── config/
│   ├── config_loader.py           # Existing config system
│   └── agent.yaml                 # Configuration file
└── core/
    └── observability/
        └── langfuse_config.py     # Existing Langfuse setup
```

### Pattern 1: Provider Client Factory
**What:** Factory pattern to create LLM clients based on configuration, similar to existing `get_llm_client()` in `src/core/providers/llm_client.py`

**When to use:** When you need to instantiate different LLM providers (OpenAI, Gemini) based on configuration

**Example:**
```python
# Source: Existing pattern in src/core/providers/llm_client.py
from langchain_google_genai import ChatGoogleGenerativeAI

_llm_cache: dict = {}

def get_gemini_client() -> ChatGoogleGenerativeAI:
    """Get a cached ChatGoogleGenerativeAI client configured from config.

    Returns:
        Configured ChatGoogleGenerativeAI client pointing at Gemini API.
    """
    if "gemini" in _llm_cache:
        return _llm_cache["gemini"]

    config = load_config()

    client = ChatGoogleGenerativeAI(
        model=config.llm.model,  # e.g., "gemini-2.5-flash"
        temperature=config.llm.temperature,
        max_tokens=config.llm.max_tokens,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )
    _llm_cache["gemini"] = client
    return client
```

### Pattern 2: Import Convention
**What:** Standard import pattern for LangChain provider packages

**When to use:** All imports of ChatGoogleGenerativeAI

**Example:**
```python
# Source: https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai
from langchain_google_genai import ChatGoogleGenerativeAI

# NOT this (incorrect):
# from langchain.chat_models import ChatGoogleGenerativeAI
```

### Pattern 3: Langfuse Automatic Tracing
**What:** Existing Langfuse callback handler automatically traces LangChain models without additional configuration

**When to use:** Always - existing infrastructure in `src/core/observability/langfuse_config.py` works with any LangChain model

**Example:**
```python
# Source: Existing pattern in src/core/observability/langfuse_config.py
# The callback handler is model-agnostic and traces ChatGoogleGenerativeAI automatically
callback_handler = get_langfuse_callback()
config = {"callbacks": [callback_handler]} if callback_handler else {}

# This works for both OpenAI and Gemini models
response = model.invoke(messages, config=config)
```

### Anti-Patterns to Avoid
- **Don't use absolute version pins** (e.g., `langchain-google-genai==4.2.0`) - Use caret constraints to allow security patches and minor updates
- **Don't import from langchain.chat_models** - Use provider-specific imports (`from langchain_google_genai import ...`)
- **Don't skip Poetry lock file regeneration** - Always run `poetry lock` after manual `pyproject.toml` edits to ensure consistent dependency resolution

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Google Gemini API client | Custom HTTP client for Gemini API | `langchain-google-genai` | Handles authentication, retries, streaming, error handling, rate limiting, multimodal content, and provides LangChain-compatible interface |
| LLM provider switching | Manual if/else chains for different providers | LangChain's unified chat model interface | Enables drop-in replacement of providers without changing consumer code |
| Observability/tracing | Custom logging for LLM calls | Langfuse callback handler (already integrated) | Automatically traces all LangChain models without code changes |

**Key insight:** The LangChain ecosystem provides battle-tested abstractions that handle edge cases like token streaming, retry logic, timeout handling, and multimodal inputs. Custom implementations inevitably miss edge cases that production systems expose.

## Common Pitfalls

### Pitfall 1: langchain-core Version Incompatibility
**What goes wrong:** `langchain-google-genai` requires `langchain-core >=1.2.5,<2.0.0`, but the project currently has `langchain-core 0.3.83`. Poetry will upgrade langchain-core to 1.x when installing langchain-google-genai, which may break existing code if LangChain 0.3.x is not forward-compatible with langchain-core 1.x.

**Why it happens:** Different LangChain provider packages have different langchain-core version requirements. The OpenAI provider was likely installed when langchain-core 0.3.x was current.

**How to avoid:**
1. Check if existing LangChain packages (langchain 0.3.27, langchain-openai 0.3.0, langchain-community 0.3.29) support langchain-core 1.x
2. Run `poetry add langchain-google-genai` in a test branch first
3. Review Poetry's resolution output for any conflicts
4. Test existing LangChain functionality after installation

**Warning signs:**
- Poetry shows dependency conflicts during `poetry add`
- Import errors from existing LangChain code after installation
- Type checking errors from Pydantic schema changes

### Pitfall 2: Missing GOOGLE_API_KEY Environment Variable
**What goes wrong:** `ChatGoogleGenerativeAI` initialization succeeds but fails at runtime when making API calls without the API key configured.

**Why it happens:** Unlike OpenAI's client which requires the API key at initialization, Google's client can be instantiated without it but will fail on first use.

**How to avoid:**
1. Document the GOOGLE_API_KEY requirement in .env.example
2. Add validation in configuration loading to check for the key
3. Use early initialization tests that make actual API calls

**Warning signs:**
- Import succeeds but invoke/stream methods fail with authentication errors
- Works in some environments but not others (missing env vars)

### Pitfall 3: Importing from Wrong Package
**What goes wrong:** Attempting to import `ChatGoogleGenerativeAI` from `langchain.chat_models` or other locations fails with ImportError.

**Why it happens:** LangChain's architecture has evolved to use provider-specific packages. Old tutorials or documentation may reference deprecated import paths.

**How to avoid:**
1. Always import from `langchain_google_genai` (note the underscore, not hyphen)
2. Verify imports work before proceeding with implementation
3. Use type hints and IDE auto-completion to catch import errors early

**Warning signs:**
- IDE shows red squiggles on imports
- ImportError at runtime
- Type checking tools (basedpyright) report unresolved imports

### Pitfall 4: Poetry Cache Corruption
**What goes wrong:** After installation, imports fail or wrong versions are installed despite poetry.lock showing correct versions.

**Why it happens:** Poetry's cache can become stale or corrupted, especially when switching between Python versions or after system updates.

**How to avoid:**
1. Clear Poetry cache before installation: `poetry cache clear pypi --all`
2. Use `poetry install --sync` to ensure virtual environment matches lock file
3. Verify installation with `poetry show langchain-google-genai`

**Warning signs:**
- `poetry show` output doesn't match poetry.lock
- Imports work in one terminal but not another
- Mysterious "module not found" errors after successful installation

## Code Examples

Verified patterns from official sources:

### Basic Model Initialization
```python
# Source: https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai
from langchain_google_genai import ChatGoogleGenerativeAI
import os

# Initialize with API key from environment
model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=1.0,
    max_tokens=None,
    google_api_key=os.getenv("GOOGLE_API_KEY"),
)
```

### Standard Invocation Pattern
```python
# Source: https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai
messages = [
    ("system", "You are a helpful assistant."),
    ("human", "What is the capital of France?")
]

response = model.invoke(messages)
print(response.content)
```

### With Langfuse Tracing (Existing Pattern)
```python
# Source: Existing pattern in src/core/observability/langfuse_config.py
from src.core.observability.langfuse_config import get_langfuse_callback

# Get configured callback handler (returns None if not configured)
callback_handler = get_langfuse_callback()

# Create config with callbacks
config = {
    "callbacks": [callback_handler],
    "tags": ["gemini", "role-clustering"],
} if callback_handler else {}

# Invoke with tracing
response = model.invoke(messages, config=config)
```

### Import Verification Test
```python
# Source: Best practice for dependency verification
def test_import():
    """Verify langchain-google-genai is importable."""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        print("✓ ChatGoogleGenerativeAI import successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| google-ai-generativelanguage SDK | google-genai unified SDK | v4.0.0 (2025) | Enables both Gemini Developer API and Vertex AI support in single package |
| Separate langchain-google-vertexai package | Consolidated in langchain-google-genai | v4.0.0 | Simplified package structure, reduced dependency complexity |
| Model name "gemini-pro" | Model name "gemini-2.5-flash" | Late 2025 | Updated model naming convention, improved performance |

**Deprecated/outdated:**
- **google-ai-generativelanguage**: Replaced by google-genai SDK in langchain-google-genai v4.0.0
- **langchain.chat_models.ChatGoogleGenerativeAI**: Import from langchain_google_genai instead
- **Gemini 1.0 Pro models**: Superseded by Gemini 2.x models with better performance and features

## Open Questions

1. **langchain-core 1.x Compatibility**
   - What we know: langchain-google-genai requires langchain-core >=1.2.5
   - What's unclear: Whether all existing code using LangChain 0.3.27 is compatible with langchain-core 1.x
   - Recommendation: Test installation in isolated environment first, run existing test suite to verify compatibility

2. **Version Constraint Strategy**
   - What we know: Caret constraint (^4.0.0) allows minor and patch updates
   - What's unclear: How frequently langchain-google-genai releases breaking changes within 4.x
   - Recommendation: Use ^4.0.0 to get security updates, monitor release notes for breaking changes

3. **Migration Path for Existing Code**
   - What we know: Current code uses langchain-openai 0.3.0 pattern
   - What's unclear: Whether langchain-core 1.x upgrade will require changes to existing LangChain usage
   - Recommendation: Document current LangChain API surface area, test thoroughly after upgrade

## Sources

### Primary (HIGH confidence)
- PyPI: https://pypi.org/project/langchain-google-genai/4.2.0/ - Package metadata, version 4.2.0, dependencies
- Official LangChain Docs: https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai - Installation, import patterns, basic usage
- GitHub Source: https://github.com/langchain-ai/langchain-google/blob/main/libs/genai/pyproject.toml - Dependency requirements (langchain-core >=1.2.5,<2.0.0)
- GitHub Releases: https://github.com/langchain-ai/langchain-google/releases - Version history, v4.2.0 released January 13, 2025
- Poetry Docs: https://python-poetry.org/docs/dependency-specification/ - Version constraint best practices
- Project Files: /home/jfr4nc0/workspace/serial-linkedin-killer/pyproject.toml - Current dependency versions

### Secondary (MEDIUM confidence)
- Langfuse Docs: https://langfuse.com/docs/integrations/langchain/tracing - Automatic tracing via callback handler, model-agnostic
- GitHub Issues: https://github.com/langchain-ai/langchain-google/issues - Common problems (58 open issues), installation issues, compatibility concerns

### Tertiary (LOW confidence)
- None - All findings verified with official sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official LangChain package, verified versions from PyPI and GitHub
- Architecture: HIGH - Existing patterns in codebase match LangChain best practices
- Pitfalls: MEDIUM - langchain-core version incompatibility is documented requirement but migration impact unclear
- Compatibility: MEDIUM - langchain-core upgrade to 1.x may impact existing code (needs testing)

**Research date:** 2026-02-11
**Valid until:** 2026-03-11 (30 days - stable ecosystem)

## Critical Discovery: Dependency Upgrade Required

⚠️ **IMPORTANT**: Installing `langchain-google-genai` will force an upgrade of `langchain-core` from 0.3.83 to 1.x. This may impact:

1. **Existing LangChain packages**: langchain 0.3.27, langchain-openai 0.3.0, langchain-community 0.3.29 may need updates
2. **Application code**: Any code using langchain-core APIs may require changes
3. **Testing**: All existing LangChain functionality must be re-tested after upgrade

**Recommendation for Phase 1**:
- Accept the langchain-core upgrade as necessary
- Create Phase 1 success criteria to include: "All existing LangChain functionality still works after upgrade"
- Add verification step to run existing test suite after installation
- Document any API changes discovered during testing
