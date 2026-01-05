from runner.executor.device import Device
from runner.web.driver import WebDriver

class WebDevice(Device):
    """
    Web Browser Device Adapter.
    Adapts WebDriver to the Device interface.
    """
    
    def __init__(self, device_id: str = "web_browser_001", headless: bool = True):
        self._device_id = device_id
        self._driver = WebDriver(headless=headless)
        self._connected = False
        
        # Auto-start driver
        self.connect()
        
    @property
    def device_id(self) -> str:
        return self._device_id
    
    @property
    def device_type(self) -> str:
        return "web"
    
    def is_connected(self) -> bool:
        return self._connected
    
    def connect(self):
        try:
            self._driver.start()
            self._connected = True
        except Exception as e:
            print(f"Failed to start WebDevice: {e}")
            self._connected = False

    def disconnect(self):
        try:
            self._driver.stop()
        finally:
            self._connected = False
    
    def screenshot(self, save_path: str) -> bool:
        if not self._connected:
            return False
        res = self._driver.execute("screenshot", {"path": save_path})
        return res.get("status") == "success"
    
    def tap(self, x: int, y: int) -> bool:
        if not self._connected:
            return False
        res = self._driver.execute("click", {"x": x, "y": y})
        return res.get("status") == "success"
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        if not self._connected:
            return False
        # Map swipe to scroll.
        # Calculate delta
        dx = x1 - x2 # If scrolling down (dragging up), y2 < y1, dy > 0
        dy = y1 - y2
        res = self._driver.execute("scroll", {"x": dx, "y": dy})
        return res.get("status") == "success"
    
    def input_text(self, text: str) -> bool:
        if not self._connected:
            return False
        res = self._driver.execute("type", {"text": text})
        return res.get("status") == "success"
    
    def press_back(self) -> bool:
        if not self._connected:
            return False
        res = self._driver.execute("back", {})
        return res.get("status") == "success"
    
    def press_home(self) -> bool:
        if not self._connected:
            return False
        # Web "Home" -> Go to blank page or specific home?
        # For now, let's go to about:blank to clear state
        res = self._driver.execute("navigate", {"url": "about:blank"})
        return res.get("status") == "success"
    
    def launch_app(self, package: str) -> bool:
        if not self._connected:
            return False
        # Treat package as URL if it looks like one, otherwise maybe search?
        url = package
        if not url.startswith("http"):
            url = f"https://{package}"
            
        res = self._driver.execute("navigate", {"url": url})
        return res.get("status") == "success"
