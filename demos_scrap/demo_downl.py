import pycurl
from fake_useragent import UserAgent
from io import BytesIO
import os
import time

class DemoDownloader:
    DOWNLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "demos")

    def __init__(self, url):
        self.url = url

    def download(self, max_retries=3):
        for attempt in range(max_retries):
            try:
                buffer = BytesIO()
                c = pycurl.Curl()
                c.setopt(c.URL, self.url)
                c.setopt(c.WRITEDATA, buffer)
                c.setopt(c.FOLLOWLOCATION, True)  # Segue redirects
                c.setopt(c.MAXREDIRS, 5)  # Máximo de 5 redirects
                c.setopt(c.CONNECTTIMEOUT, 30)
                c.setopt(c.TIMEOUT, 300)  # 5 minutos timeout
                
                # Headers mais realistas para evitar bloqueios
                headers = [
                    f"User-Agent: {UserAgent().random}",
                    "Accept: */*",
                    "Accept-Language: en-US,en;q=0.9",
                    "Accept-Encoding: gzip, deflate, br",
                    "DNT: 1",
                    "Connection: keep-alive",
                    "Upgrade-Insecure-Requests: 1"
                ]
                c.setopt(c.HTTPHEADER, headers)
                c.setopt(c.SSL_VERIFYPEER, 0)  # Desativa verificação SSL se necessário
                c.setopt(c.SSL_VERIFYHOST, 0)
                c.perform()
                
                # Verifica se teve sucesso
                response_code = c.getinfo(pycurl.RESPONSE_CODE)
                c.close()
                
                if response_code == 200:
                    return buffer.getvalue()
                elif response_code == 403:
                    if attempt < max_retries - 1:
                        wait_time = 5 * (attempt + 1)
                        print(f"⚠️  403 Forbidden, tentativa {attempt + 1}/{max_retries}, aguardando {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        raise Exception(f"HTTP Error: {response_code} (Acesso bloqueado)")
                else:
                    raise Exception(f"HTTP Error: {response_code}")
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️  Erro na tentativa {attempt + 1}: {str(e)}")
                    time.sleep(2)
                else:
                    raise

    @classmethod
    def is_demo_already_downloaded(cls, filepath):
        try:
            file_path = os.path.join(cls.DOWNLOAD_FOLDER, f"{filepath.split('/')[-1]}.dem")
            return os.path.exists(file_path) and os.path.getsize(file_path) > 0
        except FileNotFoundError:
            return False

if __name__ == "__main__":
    # Open recent_matches.json and find demo links to download
    import json
    import os
    
    with open("recent_matches.json", "r") as f:
        matches = json.load(f)

    # Create demos folder if it doesn't exist
    os.makedirs("demos", exist_ok=True)

    for match in matches:
        demo_link = match.get("demo_link")
        if demo_link:
            print(f"📥 Downloading demo from {demo_link}...")
            try:
                downloader = DemoDownloader(demo_link)
                if DemoDownloader.is_demo_already_downloaded(demo_link):
                    print(f"⚠️  Demo already downloaded, skipping: {demo_link}")
                    continue
                demo_data = downloader.download()
                filename = os.path.join("demos", demo_link.split("/")[-1] + ".rar")
                with open(filename, "wb") as demo_file:
                    demo_file.write(demo_data)
                print(f"✅ Demo saved as {filename}.")
            except Exception as e:
                print(f"❌ Error downloading {demo_link}: {str(e)}")
        else:
            print(f"⚠️  No demo link for match: {match['match_link']}")