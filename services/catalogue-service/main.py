import os
import logging
import yaml
from catalogue_api import app

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

CONFIG_PATH = os.environ.get("CONFIG_PATH", "../shared/config/global_config.yaml")
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
