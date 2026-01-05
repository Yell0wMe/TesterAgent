from runner.web.device import WebDevice

def test_web_device():
    print("Testing WebDevice Adapter...")
    device = WebDevice(headless=True)
    
    if not device.is_connected():
        print("Failed to connect.")
        return

    print("Launching App (URL: https://www.bing.com)...")
    device.launch_app("https://www.bing.com")
    
    print("Taking screenshot...")
    device.screenshot("test_device_adapter.png")
    print("Saved test_device_adapter.png")
    
    device.disconnect()
    print("Test Complete.")

if __name__ == "__main__":
    test_web_device()
