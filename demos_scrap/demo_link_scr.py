###############################################################################
# Demo link scraper
#
# This script scrapes the demo link from the matches found in recent_matches.json
###############################################################################

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
from demos_scrap.pages.matches import MatchesPage
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from demos_scrap.pages import results
from pages.results import ResultsPage

BASE_URL = "https://www.hltv.org"

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

def load_matches(filename):
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

def _get_chromedriver_path():
    """Get the local chromedriver path"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    chromedriver_path = os.path.join(base_dir, "chromedriver-mac-arm64", "chromedriver")
    
    if os.path.exists(chromedriver_path):
        # Make sure it's executable
        os.chmod(chromedriver_path, 0o755)
        return chromedriver_path
    
    # Fallback to parent directory
    chromedriver_path = os.path.join(os.path.dirname(base_dir), "chromedriver-mac-arm64", "chromedriver")
    if os.path.exists(chromedriver_path):
        os.chmod(chromedriver_path, 0o755)
        return chromedriver_path
    
    return None

def process_match(match, delay=0):
    """Process a single match to extract demo link"""
    # Add staggered delay to prevent simultaneous ChromeDriver starts
    if delay > 0:
        time.sleep(delay)
    
    print(f"🔍 A processar '{match['match_link']}'")
    
    driver = None
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            # Try to use local chromedriver first
            chromedriver_path = _get_chromedriver_path()
            
            if chromedriver_path:
                print(f"✓ Usando ChromeDriver local: {chromedriver_path}")
                service = Service(chromedriver_path)
            else:
                print("⚠️  ChromeDriver local não encontrado, usando WebDriver Manager...")
                service = Service(ChromeDriverManager(driver_version='142.0.7444.176').install())
            
            driver = webdriver.Chrome(service=service, options=_create_options())
            driver.set_page_load_timeout(30)
            driver.get(match['match_link'])

            match_page = MatchesPage(driver)
            match_page.accept_cookies()
            demo_link = match_page.get_demo_link()
            
            if not demo_link:
                print("Sem demo disponível.")
                return match
                
            print(f"✅ Demo encontrada: {demo_link}\n")
            match['demo_link'] = BASE_URL + demo_link
            return match
            
        except Exception as e:
            print(f"⚠️  Erro ao processar {match['match_link']}: {str(e)}")
            if driver:
                try:
                    driver.quit()
                except:
                    pass
                driver = None
            
            if attempt < max_retries - 1:
                print(f"⚠️  Tentativa {attempt + 1} falhou, tentando novamente...")
                time.sleep(2)
            else:
                print(f"❌ Erro ao processar {match['match_link']}: {str(e)}")
                return match
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

def main(max_workers=3):
    """Main function with parallel execution
    
    Args:
        max_workers: Number of parallel browser instances (default: 3)
    """
    matches = load_matches("./recent_matches.json")
    
    print(f"🚀 Processing {len(matches)} matches with {max_workers} parallel workers...\n")
    
    # Process matches in parallel
    updated_matches = []
    matches_lock = threading.Lock()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_match = {executor.submit(process_match, match): match for match in matches}
        
        # Collect results as they complete
        for future in as_completed(future_to_match):
            try:
                result = future.result()
                with matches_lock:
                    updated_matches.append(result)
            except Exception as e:
                print(f"❌ Erro ao processar match: {str(e)}")
                # Add original match even if processing failed
                with matches_lock:
                    updated_matches.append(future_to_match[future])
    
    # Remove duplicates based on match_link
    matches = remove_duplicates(updated_matches)

    print(f"✅ {len(matches)} jogos únicos encontrados.\n")
    save_json(matches, "recent_matches.json")
    print(f"✅ Dados salvos em 'recent_matches.json'.\n")

if __name__ == "__main__":
    main(max_workers=3)  # Teste com 3 workers
