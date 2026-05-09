import os
import re

file_path = r'c:\Users\ThinkPad\Desktop\contract\backend\core\settings.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Imports
if 'import dj_database_url' not in content:
    content = content.replace('from pathlib import Path', 'from pathlib import Path\nimport os\nimport dj_database_url\nfrom dotenv import load_dotenv\n\nload_dotenv()\n')

# 2. Secret Key, Debug, Allowed Hosts
content = re.sub(r'SECRET_KEY = .*', 'SECRET_KEY = os.getenv(\'SECRET_KEY\', \'django-insecure-09jilek33ysbl1b7i(e%8bfjw@(lmlmzx!1ukr=+j^_d6zw8xu\')', content)
content = re.sub(r'DEBUG = .*', 'DEBUG = os.getenv(\'DEBUG\', \'True\') == \'True\'', content)
content = re.sub(r'ALLOWED_HOSTS = .*', 'ALLOWED_HOSTS = os.getenv(\'ALLOWED_HOSTS\', \'*\').split(\',\')', content)

# 3. Middleware (whitenoise)
if 'WhiteNoiseMiddleware' not in content:
    content = content.replace('\'django.middleware.security.SecurityMiddleware\',', '\'django.middleware.security.SecurityMiddleware\',\n    \'whitenoise.middleware.WhiteNoiseMiddleware\',')

# 4. Database
if 'dj_database_url' in content and 'sqlite3' in content and 'dj_database_url.config' not in content:
    db_replacement = '''DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600
    )
}'''
    content = re.sub(r'DATABASES = \{.*?\n\}', db_replacement, content, flags=re.DOTALL)

# 5. Static files
if 'STATIC_ROOT' not in content:
    content = content.replace('STATIC_URL = \'static/\'', 'STATIC_URL = \'static/\'\nSTATIC_ROOT = BASE_DIR / \'staticfiles\'\nSTATICFILES_STORAGE = \'whitenoise.storage.CompressedManifestStaticFilesStorage\'')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Settings updated successfully.")
