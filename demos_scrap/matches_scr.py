import requests
from bs4 import BeautifulSoup
import re
import time
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from fake_useragent import UserAgent

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pages.results import ResultsPage

BASE_URL = "https://www.hltv.org"

def get_recent_matches(team_url, driver):
    """Obtém os jogos recentes da equipa"""
    driver.get(team_url)
    time.sleep(2)  # Espera um pouco para a página carregar
    
    # Verifica se há verificação de bot (Cloudflare ou similar)
    if ".captcha-container" in driver.page_source:
        print("🚨 Página de verificação de bot detectada. Tirando screenshot...")
        driver.save_screenshot('bot_check_screenshot.png')
        print("Screenshot salvo como 'bot_check_screenshot.png'")
        return []
    
    results_page = ResultsPage(driver)
    results_page.accept_cookies()
    results_page.load_entire_page()
    matches_rows = results_page.get_matches_rows()
    return matches_rows

def remove_duplicates(matches: dict) -> dict:
    """Remove jogos duplicados com base no link do jogo"""
    unique_matches_set = set()
    matches_unique = []
    for match in matches:
        if match['match_link'] not in unique_matches_set:
            unique_matches_set.add(match['match_link'])
            matches_unique.append(match)
    return matches_unique

def save_json(data, filename):
    """Salva os dados em formato JSON"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_teams_ids(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def _create_options():
    options = Options()
    options.binary_location = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
    # options.add_argument("--headless")  # Executa em modo headless para evitar popups visuais
    options.add_argument(f"--user-agent={UserAgent().random}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-features=VizDisplayCompositor")
    return options

def process_team(team_name, team_id):
    """Process a single team to get their recent matches"""
    print(f"🔍 A procurar '{team_name}'...")
    
    driver = None
    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager(driver_version='142.0.7444.176').install()),
            options=_create_options()
        )
        
        team_url = f"{BASE_URL}/results/?team={team_id}"
        print(f"✅ Página da equipa: {team_url}")
        print("📅 A obter últimos jogos...\n")
        
        current_team_matches = get_recent_matches(team_url, driver)
        if not current_team_matches:
            print("Sem resultados.")
            return []
        
        print(f"✅ {len(current_team_matches)} jogos encontrados.\n")
        return current_team_matches
        
    except Exception as e:
        print(f"❌ Erro ao processar equipa {team_name}: {str(e)}")
        return []
    finally:
        if driver:
            driver.quit()

def main(max_workers=3):
    """Main function with parallel execution
    
    Args:
        max_workers: Number of parallel browser instances (default: 3)
    """
    teams_ids = load_teams_ids("./demos_scrap/teams.json")
    
    print(f"🚀 Processing {len(teams_ids)} teams with {max_workers} parallel workers...\n")
    
    matches = []
    matches_lock = threading.Lock()
    
    # Process teams in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_team = {executor.submit(process_team, team_name, team_id): team_name 
                          for team_name, team_id in teams_ids.items()}
        
        # Collect results as they complete
        for future in as_completed(future_to_team):
            try:
                team_matches = future.result()
                with matches_lock:
                    matches.extend(team_matches)
            except Exception as e:
                team_name = future_to_team[future]
                print(f"❌ Erro ao processar equipa {team_name}: {str(e)}")
    
    # Remove duplicates based on match_link
    matches = remove_duplicates(matches)

    print(f"✅ {len(matches)} jogos únicos encontrados.\n")
    save_json(matches, "recent_matches.json")
    print(f"✅ Dados salvos em 'recent_matches.json'.\n")

if __name__ == "__main__":
    main()
