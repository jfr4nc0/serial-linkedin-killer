"""
Chrome profile selection utility for browser automation.
Discovers available Chrome profiles and allows user selection.
"""

import json
import os
import platform
from pathlib import Path
from typing import Dict, List, Optional


class ChromeProfileSelector:
    """Manages Chrome profile discovery and selection."""

    def __init__(self):
        self.chrome_data_dir = self._get_chrome_data_directory()

    def _get_chrome_data_directory(self) -> Path:
        """Get the Chrome user data directory based on the operating system."""
        system = platform.system()

        if system == "Linux":
            return Path.home() / ".config" / "google-chrome"
        elif system == "Darwin":  # macOS
            return Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
        elif system == "Windows":
            return Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data"
        else:
            raise OSError(f"Unsupported operating system: {system}")

    def discover_profiles(self) -> Dict[str, Dict]:
        """Discover all available Chrome profiles."""
        if not self.chrome_data_dir.exists():
            return {}

        profiles = {}

        # Check Default profile
        default_path = self.chrome_data_dir / "Default"
        if default_path.exists():
            profile_info = self._get_profile_info(default_path, "Default")
            if profile_info:
                profiles["Default"] = profile_info

        # Check numbered profiles (Profile 1, Profile 2, etc.)
        for item in self.chrome_data_dir.iterdir():
            if item.is_dir() and item.name.startswith("Profile "):
                profile_info = self._get_profile_info(item, item.name)
                if profile_info:
                    profiles[item.name] = profile_info

        return profiles

    def _get_profile_info(
        self, profile_path: Path, profile_name: str
    ) -> Optional[Dict]:
        """Extract profile information from Chrome profile directory."""
        try:
            # Check if this is a valid Chrome profile
            preferences_file = profile_path / "Preferences"
            if not preferences_file.exists():
                return None

            # Try to read profile name from preferences
            display_name = profile_name
            try:
                with open(preferences_file, "r", encoding="utf-8") as f:
                    prefs = json.load(f)
                    profile_info = prefs.get("profile", {})
                    display_name = profile_info.get("name", profile_name)
            except (json.JSONDecodeError, KeyError):
                pass

            # Check for login data (indicates if user might be logged into sites)
            login_data_file = profile_path / "Login Data"
            has_saved_passwords = login_data_file.exists()

            # Check cookies (indicates recent activity)
            cookies_file = profile_path / "Cookies"
            has_cookies = cookies_file.exists()

            return {
                "name": display_name,
                "path": str(profile_path),
                "has_saved_passwords": has_saved_passwords,
                "has_cookies": has_cookies,
                "last_used": self._get_last_used_time(profile_path),
            }

        except Exception:
            return None

    def _get_last_used_time(self, profile_path: Path) -> Optional[str]:
        """Get the last used time of the profile."""
        try:
            # Check modification time of History file as indicator of recent use
            history_file = profile_path / "History"
            if history_file.exists():
                import datetime

                mtime = os.path.getmtime(history_file)
                return datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass
        return None

    def select_profile_interactive(self) -> Optional[str]:
        """Interactive profile selection menu."""
        profiles = self.discover_profiles()

        if not profiles:
            print("❌ No Chrome profiles found!")
            print(f"Chrome data directory: {self.chrome_data_dir}")
            return None

        print("\n" + "=" * 60)
        print("🔍 Available Chrome Profiles")
        print("=" * 60)

        # Display profiles with details
        profile_list = list(profiles.items())
        for i, (profile_key, info) in enumerate(profile_list, 1):
            print(f"\n{i}. {info['name']} ({profile_key})")
            print(f"   Path: {info['path']}")
            if info["last_used"]:
                print(f"   Last used: {info['last_used']}")

            indicators = []
            if info["has_cookies"]:
                indicators.append("🍪 Has cookies")
            if info["has_saved_passwords"]:
                indicators.append("🔑 Has saved passwords")

            if indicators:
                print(f"   Status: {' | '.join(indicators)}")

        print(f"\n{len(profile_list) + 1}. Create new temporary profile")
        print("=" * 60)

        # Get user selection
        while True:
            try:
                choice = input(
                    f"\nSelect a profile (1-{len(profile_list) + 1}) or 'q' to quit: "
                ).strip()

                if choice.lower() == "q":
                    return None

                choice_num = int(choice)

                if choice_num == len(profile_list) + 1:
                    print("✅ Using temporary profile")
                    return None  # No profile path = temporary profile

                if 1 <= choice_num <= len(profile_list):
                    selected_profile = profile_list[choice_num - 1][1]
                    print(f"✅ Selected profile: {selected_profile['name']}")
                    return selected_profile["path"]
                else:
                    print(
                        f"❌ Please enter a number between 1 and {len(profile_list) + 1}"
                    )

            except ValueError:
                print("❌ Please enter a valid number or 'q' to quit")
            except KeyboardInterrupt:
                print("\n❌ Selection cancelled")
                return None

    def get_profile_from_env_or_select(self) -> Optional[str]:
        """Get profile from environment variable or interactive selection."""
        # First check environment variable
        env_profile = os.getenv("CHROME_PROFILE_PATH")
        if env_profile and Path(env_profile).exists():
            print(f"✅ Using profile from environment: {env_profile}")
            return env_profile

        # If no env variable or invalid path, show interactive selection
        print("🔧 No valid CHROME_PROFILE_PATH found in environment.")
        return self.select_profile_interactive()


# Global instance for easy access
chrome_profile_selector = ChromeProfileSelector()
