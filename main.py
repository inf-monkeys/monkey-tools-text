from src.config import config_data
from src.server import app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=config_data.get('server', {}).get('port', 8890))
