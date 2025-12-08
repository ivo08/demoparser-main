from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .base import HltvBasePage

class MatchesPage(HltvBasePage):
    def __init__(self, driver: WebDriver):
        super().__init__(driver)
    
    def get_demo_link(self):
        """Obtém o link para download do demo, se disponível"""
        try:
            # Wait until the demo element has the text indicating a demo is available
            # Regex to find the demo link button with '/download/demo/' in its attribute
            # Example: <a data-demo-link="/download/demo/12345/" ...>
            demo_button = WebDriverWait(self.driver, 10).until(
                EC.text_to_be_present_in_element_attribute((By.XPATH, '//*[@data-demo-link]'), 'data-demo-link', '/download/demo/')
            )
            demo_button = self.driver.find_element(By.XPATH, '//*[@data-demo-link]')
            demo_link = demo_button.get_attribute('data-demo-link')

            demo_button.click()  # Click to initiate download if necessary

            return demo_link
        except Exception as e:
            print("ℹ️ Demo não disponível ou erro ao obter o link:", e)
            return None