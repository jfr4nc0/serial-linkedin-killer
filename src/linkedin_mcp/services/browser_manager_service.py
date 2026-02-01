import atexit
import os
import random
import shutil
import signal
import sys
import time
import weakref
from typing import Optional

import undetected_chromedriver as uc
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from webdriver_manager.firefox import GeckoDriverManager

from src.linkedin_mcp.interfaces.services import IBrowserManager
from src.linkedin_mcp.utils.logging_config import get_mcp_logger
from src.linkedin_mcp.utils.user_agent_rotator import user_agent_rotator


class BrowserManagerService(IBrowserManager):
    """Manages browser instances for LinkedIn automation."""

    # Track all live instances via weak references for cleanup on exit
    _instances: list[weakref.ref] = []

    def __init__(
        self,
        headless: bool = False,
        use_undetected: bool = True,
        browser_type: str = "chrome",
        chrome_version: Optional[int] = None,
        chrome_binary_path: Optional[str] = None,
    ):
        self.headless = headless
        self.use_undetected = use_undetected
        self.browser_type = browser_type.lower()
        self.chrome_version = chrome_version
        self.chrome_binary_path = chrome_binary_path
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        BrowserManagerService._instances.append(weakref.ref(self))

    def __del__(self):
        """Safety net: cleanup browser if object is garbage collected."""
        try:
            self.close_browser()
        except Exception:
            pass

    def _get_chrome_options(self) -> Options:
        """Configure Chrome options for LinkedIn automation."""
        options = Options()
        options.page_load_strategy = "eager"

        if self.headless:
            options.add_argument("--headless")
        else:
            options.add_argument("--start-maximized")

        # Basic options for compatibility
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")

        # Performance and memory options
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--renderer-process-limit=1")
        options.add_argument("--js-flags=--max-old-space-size=256")

        # Use ~/chrome directory for user data with undetected-chromedriver
        chrome_user_data = os.path.expanduser("~/chrome")
        options.add_argument(f"--user-data-dir={chrome_user_data}")

        # Set custom Chrome binary path if specified
        if self.chrome_binary_path:
            options.binary_location = self.chrome_binary_path

        return options

    def _start_firefox(self) -> webdriver.Firefox:
        """Start Firefox as fallback when Chrome fails."""
        firefox_options = FirefoxOptions()
        firefox_options.page_load_strategy = "eager"

        if self.headless:
            firefox_options.add_argument("--headless")

        # Set preferences directly on options (Selenium 4.x style)
        firefox_options.set_preference("browser.startup.homepage", "about:blank")
        firefox_options.set_preference("startup.homepage_welcome_url", "about:blank")
        firefox_options.set_preference(
            "startup.homepage_welcome_url.additional", "about:blank"
        )
        firefox_options.set_preference("browser.download.folderList", 2)
        firefox_options.set_preference(
            "browser.download.manager.showWhenStarting", False
        )
        firefox_options.set_preference("browser.download.dir", "/tmp")
        firefox_options.set_preference(
            "browser.helperApps.neverAsk.saveToDisk", "application/pdf"
        )

        # Auto-install GeckoDriver
        service = webdriver.firefox.service.Service(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=firefox_options)

        return driver

    def _start_chrome(self) -> webdriver.Chrome:
        """Start Chrome browser."""
        options = self._get_chrome_options()

        if self.use_undetected:
            # Use explicit version if provided, otherwise auto-detect
            return uc.Chrome(options=options, version_main=self.chrome_version)
        else:
            service = Service(ChromeDriverManager().install())
            return webdriver.Chrome(service=service, options=options)

    def _start_chromium(self) -> webdriver.Chrome:
        """Start Chromium browser."""
        options = self._get_chrome_options()

        if self.use_undetected:
            # Note: undetected-chromedriver might not work with Chromium
            # Fall back to regular webdriver
            service = Service(
                ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
            )
            return webdriver.Chrome(service=service, options=options)
        else:
            service = Service(
                ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
            )
            return webdriver.Chrome(service=service, options=options)

    def start_browser(self) -> webdriver.Chrome:
        """Start and configure the browser based on browser_type."""

        if self.browser_type == "firefox":
            print("Starting Firefox...")
            try:
                self.driver = self._start_firefox()
                print("Firefox started successfully")
            except Exception as e:
                print(f"Firefox failed: {str(e)}")
                print("Trying Chrome as fallback...")
                try:
                    self.driver = self._start_chrome()
                    print("Chrome started successfully")
                except Exception as chrome_error:
                    print(f"Chrome also failed: {str(chrome_error)}")
                    raise e
        elif self.browser_type == "chromium":
            print("Starting Chromium...")
            try:
                self.driver = self._start_chromium()
                print("Chromium started successfully")
            except Exception as e:
                print(f"Chromium failed: {str(e)}")
                print("Trying Chrome as fallback...")
                try:
                    self.driver = self._start_chrome()
                    print("Chrome started successfully")
                except Exception as chrome_error:
                    print(f"Chrome also failed: {str(chrome_error)}")
                    print("Trying Firefox as final fallback...")
                    try:
                        self.driver = self._start_firefox()
                        print("Firefox started successfully")
                    except Exception as firefox_error:
                        print(f"All browsers failed: {str(firefox_error)}")
                        raise e
        else:  # Default to chrome
            print("Starting Chrome...")
            try:
                self.driver = self._start_chrome()
                print("Chrome started successfully")
            except Exception as e:
                print(f"Chrome failed: {str(e)}")
                print("Trying Firefox as fallback...")
                try:
                    self.driver = self._start_firefox()
                    print("Firefox started successfully")
                except Exception as firefox_error:
                    print(f"Firefox also failed: {str(firefox_error)}")
                    raise e

        # Remove webdriver property
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        self.wait = WebDriverWait(self.driver, 10)
        return self.driver

    def close_browser(self):
        """Close the browser and cleanup resources."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                self._force_kill_browser()
            self.driver = None
            self.wait = None
            self._clean_chrome_cache()

    def _force_kill_browser(self):
        """Force kill browser processes if quit() fails."""
        try:
            import psutil

            if hasattr(self.driver, "service") and hasattr(
                self.driver.service, "process"
            ):
                proc = self.driver.service.process
                if proc and proc.pid:
                    parent = psutil.Process(proc.pid)
                    for child in parent.children(recursive=True):
                        try:
                            child.kill()
                        except psutil.NoSuchProcess:
                            pass
                    try:
                        parent.kill()
                    except psutil.NoSuchProcess:
                        pass
        except ImportError:
            # psutil not available, try os.kill as fallback
            try:
                if (
                    hasattr(self.driver, "service")
                    and hasattr(self.driver.service, "process")
                    and self.driver.service.process
                ):
                    os.kill(self.driver.service.process.pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
        except Exception:
            pass

    @staticmethod
    def _clean_chrome_cache():
        """Remove heavy Chrome cache directories to prevent disk/memory growth."""
        chrome_dir = os.path.expanduser("~/chrome")
        for subdir in ["Default/Cache", "Default/Code Cache", "Default/Service Worker"]:
            path = os.path.join(chrome_dir, subdir)
            if os.path.isdir(path):
                try:
                    shutil.rmtree(path)
                except Exception:
                    pass

    @classmethod
    def cleanup_all(cls):
        """Cleanup all browser instances. Called on process exit."""
        for ref in cls._instances:
            instance = ref()
            if instance is not None:
                try:
                    instance.close_browser()
                except Exception:
                    pass
        cls._instances.clear()

    # Interface methods
    def get_driver(self):
        """Get the current WebDriver instance."""
        if not self.driver:
            self.start_browser()
        return self.driver

    def navigate_to_job(self, job_id: str) -> None:
        """Navigate to a specific job page."""
        if not self.driver:
            self.start_browser()

        job_url = f"https://www.linkedin.com/jobs/view/{job_id}/"
        self.driver.get(job_url)

        # Wait for page to load
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "main")))

    def cleanup(self) -> None:
        """Clean up browser resources."""
        self.close_browser()

    def navigate_to_linkedin(self):
        """Navigate to LinkedIn homepage."""
        if not self.driver:
            raise RuntimeError("Browser not started. Call start_browser() first.")

        self.driver.get("https://www.linkedin.com")
        time.sleep(1)

    def wait_for_element(self, by: By, value: str, timeout: int = 10):
        """Wait for an element to be present."""
        if not self.wait:
            raise RuntimeError("Browser not started. Call start_browser() first.")

        return self.wait.until(EC.presence_of_element_located((by, value)))

    def wait_for_clickable(self, by: By, value: str, timeout: int = 10):
        """Wait for an element to be clickable."""
        if not self.wait:
            raise RuntimeError("Browser not started. Call start_browser() first.")

        return self.wait.until(EC.element_to_be_clickable((by, value)))

    def random_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Add random delay to mimic human behavior."""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)


# --- Module-level cleanup handlers ---


def _cleanup_browsers(*args):
    """Cleanup all browser instances on process exit."""
    BrowserManagerService.cleanup_all()


atexit.register(_cleanup_browsers)


def _signal_handler(sig, frame):
    """Handle SIGTERM/SIGINT by cleaning up browsers then exiting."""
    _cleanup_browsers()
    sys.exit(0)


# Only register signal handlers if not in a thread
import threading

if threading.current_thread() is threading.main_thread():
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)
