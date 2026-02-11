"""Simple debug script for message sending - bypasses all complexity."""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.config_loader import load_config
from src.linkedin_mcp.services.employee_outreach_service import EmployeeOutreachService

# Target profile - change this to test
TARGET_PROFILE_URL = "https://www.linkedin.com/in/javier-zaninovich/"
TARGET_NAME = "Javier Zaninovich"
MESSAGE = "Hola Javier, ¿cómo estás?\n\nVimos tu trabajo en Tomar Inversiones. ¿Te podré consultar si tienen dolores operacionales relacionados con la automatización de procesos de inversión y gestión de portafolios? Es para research. Gracias!"

if __name__ == "__main__":
    config = load_config()

    email = os.getenv("LINKEDIN_EMAIL") or config.linkedin.email
    password = os.getenv("LINKEDIN_PASSWORD") or config.linkedin.password

    if not email or not password:
        print("ERROR: Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD")
        sys.exit(1)

    print(f"Target: {TARGET_PROFILE_URL}")
    print(f"Name: {TARGET_NAME}")
    print(f"LinkedIn account: {email}")
    print()

    service = EmployeeOutreachService()

    messages = [
        {
            "profile_url": TARGET_PROFILE_URL,
            "name": TARGET_NAME,
            "message": MESSAGE,
            "subject": "",
        }
    ]

    print("Sending message...")
    results = service.send_messages_batch(
        messages, {"email": email, "password": password}
    )

    print()
    print("--- Result ---")
    for r in results:
        print(f"  sent: {r.get('sent')}")
        print(f"  method: {r.get('method')}")
        print(f"  error: {r.get('error')}")
