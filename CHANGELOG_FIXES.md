# Stability Fixes — Browser Crashes & Message Sending

## Problem
1. PC crashes from accumulated zombie Chrome processes
2. Message sending stops after 2-3 messages
3. ~20 seconds wasted re-authenticating on every batch

## Changes

### 1. Browser reuse (`browser_manager_service.py`)
- `start_browser()` now checks if the current driver is still responsive via `_is_browser_alive()`. If alive, returns the existing browser instead of creating a duplicate.
- If the driver reference exists but is dead, cleans it up before starting fresh.

### 2. Zombie Chrome process cleanup (`browser_manager_service.py`)
- New `_kill_zombie_chrome()` method kills orphaned `chrome`/`chromedriver` processes that use the `~/chrome` user-data-dir. Runs automatically before starting a fresh browser.
- Uses `psutil` with graceful fallback if not installed.

### 3. JS heap increase (`browser_manager_service.py`)
- `--max-old-space-size` increased from `256` to `512` MB to prevent heap exhaustion on long-running sessions with many page navigations.

### 4. Profile page WebDriverWait (`message_send_graph.py`)
- `_navigate_to_profile` now uses `WebDriverWait(driver, 10)` for `.pv-top-card, .scaffold-layout, main` instead of a blind 2-3 second sleep.
- Falls back to a 3-5s blind wait if selectors have changed.
- Prevents message failures when LinkedIn pages load slowly.

### 5. Auth skip on reused browser (`employee_outreach_service.py`)
- `_ensure_authenticated()` now calls `auth_service.is_authenticated()` first.
- If the browser is already open and logged in, skips the full login graph entirely.
- Saves ~20 seconds per batch (2x 10s timeouts looking for non-existent login fields).

### 6. Bool env var casting (`config_loader.py`)
- Fixed `bool("false")` returning `True`. Now correctly handles `"false"`, `"0"`, `"no"`, `"off"` as `False`.
- Latent bug — no boolean env vars are mapped yet, but prevents future issues.

## Files Modified
- `src/linkedin_mcp/services/browser_manager_service.py`
- `src/linkedin_mcp/graphs/message_send_graph.py`
- `src/linkedin_mcp/services/employee_outreach_service.py`
- `src/config/config_loader.py`
