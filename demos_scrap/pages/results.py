from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .base import HltvBasePage

class ResultsPage(HltvBasePage):
    def __init__(self, driver: WebDriver):
        super().__init__(driver)

    def get_matches_rows(self):
        """Obtém as linhas de jogos recentes"""
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'result-con'))
        )
        matches_rows_elements = self.driver.find_elements(By.CLASS_NAME, 'result-con')

        matches_rows = [self._get_match_data(row) for row in matches_rows_elements]
        return matches_rows
    
    def _get_match_data(self, match_row):
        """Extrai os dados de um jogo a partir de uma linha"""
        # Get teams
        team_1 = match_row.find_element(By.CLASS_NAME, 'team1').text
        team_2 = match_row.find_element(By.CLASS_NAME, 'team2').text

        # Get scores
        score_td_element = match_row.find_element(By.CLASS_NAME, 'result-score')
        score_span_elements = score_td_element.find_elements(By.TAG_NAME, 'span')
        score_team_1, score_team_2 = [elem.text for elem in score_span_elements]

        # Get match link
        match_link = match_row.find_element(By.TAG_NAME, 'a').get_attribute('href')
        
        return {
            'team_1': team_1,
            'team_2': team_2,
            'score_team_1': score_team_1,
            'score_team_2': score_team_2,
            'match_link': match_link
        }
    
    def load_entire_page(self):
        """Carrega toda a página de resultados, se necessário"""
        scrolls_limit = 20  # Limite de scrolls para evitar loops infinitos
        scrolls_done = 0
        previous_count = 0
        while scrolls_done < scrolls_limit:
            # Conta os elementos atuais
            current_count = len(self.driver.find_elements(By.CLASS_NAME, 'results-sublist'))
            if current_count == previous_count and scrolls_done > 0:
                # Não carregou mais elementos
                break
            previous_count = current_count
            
            # Scroll para o fundo
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Espera por novos elementos
            try:
                WebDriverWait(self.driver, 5).until(
                    lambda driver: len(driver.find_elements(By.CLASS_NAME, 'results-sublist')) > current_count
                )
            except:
                # Timeout, assume que não há mais
                break
            
            scrolls_done += 1
        
        if scrolls_done == scrolls_limit:
            print("⚠️ Limite de scrolls atingido, pode não ter carregado todos os resultados.")
        else:
            print(f"✅ Página carregada após {scrolls_done} scrolls.")