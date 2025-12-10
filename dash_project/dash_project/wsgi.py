import os
import sys
from pathlib import Path
from django.core.wsgi import get_wsgi_application

# Ensure repo root on sys.path so `backend` imports succeed when running under WSGI
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dash_project.settings')

application = get_wsgi_application()
