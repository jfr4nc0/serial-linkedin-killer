"""
Simple profile confirmation utility for Chrome profile selection.
Prompts user to manually select profile before continuing with LinkedIn auth.
"""

import os

from dotenv import load_dotenv


class ProfileConfirmation:
    """Handles user confirmation for Chrome profile selection."""

    def __init__(self):
        load_dotenv()

    def prompt_profile_selection(self) -> bool:
        """Prompt user to select Chrome profile manually and confirm when ready."""

        profile_path = os.getenv("CHROME_PROFILE_PATH")

        print("\n" + "=" * 60)
        print("🔧 CHROME PROFILE SETUP")
        print("=" * 60)

        if profile_path:
            print(f"📁 Profile path configured: {profile_path}")
            print("✅ Chrome will use the configured profile from CHROME_PROFILE_PATH")
        else:
            print("⚠️  No CHROME_PROFILE_PATH configured")
            print("🔄 Chrome will create a temporary profile")

        print("\n📋 INSTRUCTIONS:")
        print("1. Chrome browser will open in 2 seconds")
        print(
            "2. If profile selection appears, it will auto-fallback to temporary profile"
        )
        print("3. LinkedIn authentication will start automatically")

        print("\n⏳ Starting...")
        print("=" * 60)

        try:
            import time

            time.sleep(0.5)
            print("🚀 Starting LinkedIn authentication...")
            return True

        except KeyboardInterrupt:
            print("\n❌ Authentication cancelled by user")
            return False

    def prompt_browser_ready(self) -> bool:
        """Prompt user to confirm browser is ready with correct profile."""

        print("\n" + "=" * 50)
        print("🌐 BROWSER PROFILE CONFIRMATION")
        print("=" * 50)
        print("📋 Please confirm:")
        print("• Chrome browser is open")
        print("• You're using the correct Chrome profile")
        print("• You're ready to start LinkedIn authentication")

        try:
            response = input(
                "\n✅ Is everything ready? Press ENTER to continue or 'q' to quit: "
            ).strip()

            if response.lower() == "q":
                print("❌ Process cancelled by user")
                return False

            return True

        except KeyboardInterrupt:
            print("\n❌ Process cancelled by user")
            return False


# Global instance for easy access
profile_confirmation = ProfileConfirmation()
