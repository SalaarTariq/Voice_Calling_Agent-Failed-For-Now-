"""
WhatsApp Client - Stub (console) and Real (Selenium) modes
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import List
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
        pass

    @abstractmethod
    def get_new_messages(self) -> List[WhatsAppMessage]:
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        pass


class WhatsAppStubClient(WhatsAppClient):
    """Console-based stub for testing without real WhatsApp"""

    def __init__(self):
        self.message_queue = []
        logger.info("WhatsApp Stub Client initialized (Console mode)")

    def send_message(self, phone: str, message: str) -> bool:
        print(f"\nAgent: {message}\n")
        return True

    def get_new_messages(self) -> List[WhatsAppMessage]:
        messages = self.message_queue.copy()
        self.message_queue.clear()
        return messages

    def add_test_message(self, phone: str, text: str):
        self.message_queue.append(WhatsAppMessage(phone=phone, text=text))

    def is_connected(self) -> bool:
        return True


class WhatsAppSeleniumClient(WhatsAppClient):
    """
    Real WhatsApp Web client using Selenium.
    Requires Chrome and a logged-in WhatsApp Web session.
    NOT production-grade - use WhatsApp Business API for production.
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

            options = webdriver.ChromeOptions()
            options.add_argument("--user-data-dir=./whatsapp_session")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")

            self.driver = webdriver.Chrome(
                service=ChromeService(ChromeDriverManager().install()),
                options=options,
            )

            self.driver.get("https://web.whatsapp.com")
            logger.info("WhatsApp Selenium Client initialized")
            logger.warning("Please scan QR code if this is first time")

        except ImportError:
            raise ImportError("Selenium not installed. Run: pip install selenium webdriver-manager")

    def send_message(self, phone: str, message: str) -> bool:
        try:
            from selenium.webdriver.support import expected_conditions as EC

            phone_clean = phone.replace(" ", "").replace("-", "")
            url = f"https://web.whatsapp.com/send?phone={phone_clean}"
            self.driver.get(url)

            wait = self.WebDriverWait(self.driver, 30)
            message_box = wait.until(
                EC.presence_of_element_located(
                    (self.By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
                )
            )

            message_box.click()
            message_box.send_keys(message)

            send_button = self.driver.find_element(
                self.By.XPATH, '//button[@data-tab="11"]'
            )
            send_button.click()

            logger.info(f"Message sent to {phone}")
            return True

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    def get_new_messages(self) -> List[WhatsAppMessage]:
        return []

    def is_connected(self) -> bool:
        try:
            self.driver.find_element(self.By.XPATH, '//div[@id="pane-side"]')
            return True
        except Exception:
            return False

    def close(self):
        if hasattr(self, "driver"):
            self.driver.quit()


def get_whatsapp_client() -> WhatsAppClient:
    """Get WhatsApp client based on WHATSAPP_MODE env var"""
    mode = os.getenv("WHATSAPP_MODE", "stub").lower()

    if mode == "stub":
        return WhatsAppStubClient()
    elif mode == "real":
        return WhatsAppSeleniumClient()
    else:
        logger.warning(f"Invalid WHATSAPP_MODE: {mode}, falling back to stub")
        return WhatsAppStubClient()
