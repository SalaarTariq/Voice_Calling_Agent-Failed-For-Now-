"""
WhatsApp Client - Two modes: stub (console) and real (Selenium automation)
For MVP, we primarily use stub mode for testing
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class WhatsAppMessage:
    """Represents a WhatsApp message"""
    def __init__(self, phone: str, text: str, timestamp: str = None):
        self.phone = phone
        self.text = text
        self.timestamp = timestamp
    
    def __repr__(self):
        return f"WhatsAppMessage(phone='{self.phone}', text='{self.text[:30]}...')"


class WhatsAppClient(ABC):
    """Abstract WhatsApp client interface"""
    
    @abstractmethod
    def send_message(self, phone: str, message: str) -> bool:
        """Send a message to a phone number"""
        pass
    
    @abstractmethod
    def get_new_messages(self) -> List[WhatsAppMessage]:
        """Get new unread messages"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if client is connected"""
        pass


class WhatsAppStubClient(WhatsAppClient):
    """
    Console-based WhatsApp stub for testing
    Simulates WhatsApp via terminal input/output
    """
    
    def __init__(self):
        self.message_queue = []
        logger.info("WhatsApp Stub Client initialized (Console mode)")
    
    def send_message(self, phone: str, message: str) -> bool:
        """Print message to console"""
        print("\n" + "="*60)
        print(f"📱 WhatsApp Message to {phone}")
        print("="*60)
        print(message)
        print("="*60 + "\n")
        return True
    
    def get_new_messages(self) -> List[WhatsAppMessage]:
        """
        Get messages from console input
        In real usage, this would be called in a loop
        """
        # For stub, messages are provided by the handler
        messages = self.message_queue.copy()
        self.message_queue.clear()
        return messages
    
    def add_test_message(self, phone: str, text: str):
        """Add a test message (for console testing)"""
        self.message_queue.append(WhatsAppMessage(phone=phone, text=text))
    
    def is_connected(self) -> bool:
        return True


class WhatsAppSeleniumClient(WhatsAppClient):
    """
    Real WhatsApp Web client using Selenium
    NOTE: Requires logged-in WhatsApp Web session
    This is NOT production-grade but works for MVP
    """
    
    def __init__(self):
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service as ChromeService
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            
            self.By = By
            self.WebDriverWait = WebDriverWait
            
            # Set up Chrome with persistent session
            options = webdriver.ChromeOptions()
            options.add_argument("--user-data-dir=./whatsapp_session")  # Persist login
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            self.driver = webdriver.Chrome(
                service=ChromeService(ChromeDriverManager().install()),
                options=options
            )
            
            # Open WhatsApp Web
            self.driver.get("https://web.whatsapp.com")
            logger.info("WhatsApp Selenium Client initialized")
            logger.warning("Please scan QR code if this is first time")
            
            self.last_message_ids = set()
            
        except ImportError:
            raise ImportError("Selenium not installed. Run: pip install selenium webdriver-manager")
    
    def send_message(self, phone: str, message: str) -> bool:
        """Send message via WhatsApp Web"""
        try:
            from selenium.webdriver.support import expected_conditions as EC
            import urllib.parse
            
            # Format phone number (remove spaces, dashes)
            phone_clean = phone.replace(" ", "").replace("-", "")
            
            # Open chat using URL
            url = f"https://web.whatsapp.com/send?phone={phone_clean}"
            self.driver.get(url)
            
            # Wait for message box
            wait = self.WebDriverWait(self.driver, 30)
            message_box = wait.until(
                EC.presence_of_element_located((self.By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'))
            )
            
            # Type and send
            message_box.click()
            message_box.send_keys(message)
            
            # Find and click send button
            send_button = self.driver.find_element(self.By.XPATH, '//button[@data-tab="11"]')
            send_button.click()
            
            logger.info(f"Message sent to {phone}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    def get_new_messages(self) -> List[WhatsAppMessage]:
        """
        Poll for new messages
        This is simplified - production would need more robust logic
        """
        try:
            # This is a placeholder - real implementation would:
            # 1. Check for unread message indicators
            # 2. Parse message content
            # 3. Track which messages are new
            # For MVP, we'll return empty (focus on sending)
            return []
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return []
    
    def is_connected(self) -> bool:
        """Check if WhatsApp Web is connected"""
        try:
            # Check if we can find main page elements
            self.driver.find_element(self.By.XPATH, '//div[@id="pane-side"]')
            return True
        except:
            return False
    
    def close(self):
        """Close the browser"""
        if hasattr(self, 'driver'):
            self.driver.quit()


def get_whatsapp_client() -> WhatsAppClient:
    """Get WhatsApp client based on environment configuration"""
    mode = os.getenv("WHATSAPP_MODE", "stub").lower()
    
    if mode == "stub":
        return WhatsAppStubClient()
    elif mode == "real":
        return WhatsAppSeleniumClient()
    else:
        logger.warning(f"Invalid WHATSAPP_MODE: {mode}, using stub")
        return WhatsAppStubClient()
