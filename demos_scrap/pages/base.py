from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class HltvBasePage:
    def __init__(self, driver: WebDriver):
        self.driver = driver

    def accept_cookies(self):
        """Aceita o banner de cookies, se presente"""
        try:
            accept_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, 'CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll'))
            )
            accept_button.click()
            print("✅ Cookies aceites.")
        except:
            print("ℹ️ Banner de cookies não encontrado.")