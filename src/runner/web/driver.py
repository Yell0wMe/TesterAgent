from typing import Optional, Dict, Any
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext

class WebDriver:
    """
    Web Driver implementation using Playwright (Sync).
    Provides a unified interface for web automation similar to ADB for phones.
    """
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def start(self):
        """Start the browser session."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=["--no-sandbox", "--disable-infobars"]
        )
        self.context = self.browser.new_context(
            viewport={"width": 1280, "height": 720},
            device_scale_factor=1,
        )
        self.page = self.context.new_page()

    def stop(self):
        """Stop and cleanup."""
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an action.
        
        Supported actions:
        - navigate(url)
        - click(selector / x,y)
        - type(text)
        - scroll(direction / x,y)
        - screenshot(path)
        - back()
        """
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")

        result = {"status": "success"}

        try:
            if action.lower() == "navigate":
                self.page.goto(params.get("url"), timeout=30000)
            
            elif action.lower() == "click":
                timeout = params.get("timeout", 5000)
                if "x" in params and "y" in params:
                    self.page.mouse.click(float(params["x"]), float(params["y"]))
                else:
                    # Semantic Locator Strategy
                    target = None
                    if "selector" in params:
                        # Legacy/Fallback
                        s = params["selector"]
                        if s.startswith("#") or s.startswith("."):
                             target = self.page.locator(s)
                        else:
                             # Treat as label/text
                             label = s
                             target = self.page.get_by_text(label)
                             if target.count() == 0:
                                 target = self.page.get_by_placeholder(label)
                             if target.count() == 0:
                                 target = self.page.get_by_label(label)
                    elif "label" in params:
                        label = params["label"]
                        # Try Placeholder first (common for inputs)
                        target = self.page.get_by_placeholder(label)
                        if target.count() == 0:
                            # Try visible text
                            target = self.page.get_by_text(label)
                        if target.count() == 0:
                            target = self.page.get_by_label(label)
                    
                    if target and target.count() > 0:
                        target.first.click(timeout=timeout)
                    else:
                        raise ValueError(f"Could not find element by label/selector: {params}")

            elif action.lower() == "type":
                text = params.get("text", "")
                timeout = params.get("timeout", 5000)
                
                # Try to locate and fill
                target = None
                label = params.get("label") or params.get("selector")
                
                if label:
                    if label.startswith("#") or label.startswith("."):
                         target = self.page.locator(label)
                    else:
                         # Semantic Search for Input
                         target = self.page.get_by_placeholder(label)
                         if target.count() == 0:
                             target = self.page.get_by_label(label)
                         if target.count() == 0:
                             target = self.page.get_by_role("textbox", name=label)
                
                if target and target.count() > 0:
                    try:
                        target.first.click(timeout=timeout)
                        target.first.fill(text, timeout=timeout)
                    except:
                        target.first.fill(text, timeout=timeout)
                else:
                    # Fallback: Just type (assuming focus is already set or intent is global)
                    print(f"Warning: Could not find input '{label}', typing blindly.")
                    self.page.keyboard.type(text)
            
            elif action.lower() == "screenshot":
                path = params.get("path", "screenshot.png")
                self.page.screenshot(path=path)
                result["path"] = path

            elif action.lower() == "back":
                self.page.go_back()
            
            elif action.lower() == "scroll":
                # Basic scroll implementation
                x = params.get("x", 0)
                y = params.get("y", 0)
                self.page.mouse.wheel(float(x), float(y))
            
            elif action.lower() == "press":
                key = params.get("key", "Enter")
                self.page.keyboard.press(key)
            
            elif action.lower() == "get_dom":
                snapshot = self.page.accessibility.snapshot()
                result["dom"] = snapshot
            
            elif action.lower() == "get_url":
                result["url"] = self.page.url
            
            elif action.lower() == "get_title":
                result["title"] = self.page.title()

            else:
                raise ValueError(f"Unknown action: {action}")

        except Exception as e:
            result = {"status": "error", "message": str(e)}

        # Stabilize
        import time
        time.sleep(1)
        
        return result

    def get_current_url(self) -> str:
        return self.page.url if self.page else ""

if __name__ == "__main__":
    # Test block
    def test():
        driver = WebDriver(headless=True)
        driver.start()
        print("Running Web Driver Test (Sync)...")
        driver.execute("navigate", {"url": "https://www.google.com"})
        print(f"Opened: {driver.get_current_url()}")
        driver.execute("screenshot", {"path": "test_web_sync.png"})
        print("Taken screenshot: test_web_sync.png")
        driver.stop()
    
    test()
