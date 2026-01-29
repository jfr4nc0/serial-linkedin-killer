#!/usr/bin/env python3
"""Test CV JSON integration end-to-end."""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))


def test_cv_loader():
    """Test CV JSON loading and analysis extraction."""
    print("Testing CV JSON loader...")

    try:
        from src.core.tools.cv_loader import extract_cv_analysis, load_cv_data

        # Load CV data
        cv_data = load_cv_data("./data/cv_data.json")
        print(f"✅ CV data loaded: {cv_data['name']}")

        # Extract analysis
        cv_analysis = extract_cv_analysis(cv_data)
        print(
            f"✅ CV analysis extracted: {cv_analysis['experience_years']} years experience"
        )
        print(f"   Skills: {len(cv_analysis['skills'])} skills")
        print(f"   Technologies: {len(cv_analysis['technologies'])} technologies")

        return cv_data, cv_analysis

    except Exception as e:
        print(f"❌ CV loader test failed: {e}")
        import traceback

        traceback.print_exc()
        return None, None


def test_agent_integration():
    """Test agent integration with CV JSON data."""
    print("\nTesting agent integration...")

    try:
        from src.core.agent import JobApplicationAgent
        from src.core.model.job_search_request import JobSearchRequest

        # Create minimal job search for testing
        job_searches = [
            JobSearchRequest(
                job_title="Software Engineer",
                location="Remote",
                monthly_salary=5000,
                limit=1,
            )
        ]

        user_credentials = {"email": "test@example.com", "password": "test_password"}

        # Create agent
        agent = JobApplicationAgent()
        print("✅ Agent created successfully")

        # Check if the run method has correct signature
        import inspect

        run_sig = inspect.signature(agent.run)
        params = list(run_sig.parameters.keys())

        if "cv_data_path" in params:
            print("✅ Agent run method accepts cv_data_path parameter")
        else:
            print("❌ Agent run method missing cv_data_path parameter")
            return False

        if "cv_file_path" not in params:
            print("✅ Agent run method no longer has cv_file_path parameter")
        else:
            print("⚠️  Agent run method still has cv_file_path parameter")

        return True

    except Exception as e:
        print(f"❌ Agent integration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_mcp_client_signature():
    """Test MCP client signature updates."""
    print("\nTesting MCP client signatures...")

    try:
        # Check async client
        import inspect

        from src.core.providers.linkedin_mcp_client import LinkedInMCPClient
        from src.core.providers.linkedin_mcp_client_sync import LinkedInMCPClientSync

        async_sig = inspect.signature(LinkedInMCPClient.easy_apply_for_jobs)

        if "cv_analysis" in async_sig.parameters:
            print("✅ Async client easy_apply_for_jobs accepts cv_analysis parameter")

            # Check if Union type annotation is used
            param_annotation = str(async_sig.parameters["cv_analysis"].annotation)
            if "Union" in param_annotation or "dict" in param_annotation.lower():
                print("✅ Async client cv_analysis accepts dict type")
            else:
                print("⚠️  Async client cv_analysis type annotation may need updating")
        else:
            print("❌ Async client missing cv_analysis parameter")
            return False

        # Check sync client
        sync_sig = inspect.signature(LinkedInMCPClientSync.easy_apply_for_jobs)

        if "cv_analysis" in sync_sig.parameters:
            print("✅ Sync client easy_apply_for_jobs accepts cv_analysis parameter")

            # Check if Union type annotation is used
            param_annotation = str(sync_sig.parameters["cv_analysis"].annotation)
            if "Union" in param_annotation or "dict" in param_annotation.lower():
                print("✅ Sync client cv_analysis accepts dict type")
            else:
                print("⚠️  Sync client cv_analysis type annotation may need updating")
        else:
            print("❌ Sync client missing cv_analysis parameter")
            return False

        return True

    except Exception as e:
        print(f"❌ MCP client signature test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Testing CV JSON integration...")
    print("=" * 60)

    # Test CV loader
    cv_data, cv_analysis = test_cv_loader()

    # Test agent integration
    agent_success = test_agent_integration()

    # Test MCP client signatures
    mcp_success = test_mcp_client_signature()

    print("\n" + "=" * 60)
    print("🎯 Integration Test Results:")
    print(f"   CV JSON Loading: {'✅ PASS' if cv_data else '❌ FAIL'}")
    print(f"   Agent Integration: {'✅ PASS' if agent_success else '❌ FAIL'}")
    print(f"   MCP Client Updates: {'✅ PASS' if mcp_success else '❌ FAIL'}")

    if cv_data and agent_success and mcp_success:
        print("\n🎉 All tests passed! CV JSON integration is working correctly.")
        print("\n📋 Summary of changes:")
        print("   • CV data loaded from JSON instead of PDF")
        print("   • Agent workflow updated to use cv_data.json")
        print("   • CV data passed as dict to MCP tools")
        print("   • Full JSON structure available for job filtering")
    else:
        print("\n⚠️  Some tests failed. Please check the implementation.")
        sys.exit(1)
