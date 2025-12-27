from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()

# Configuração de Limite de Requisições (Rate Limit)
# Aumentado para evitar bloqueios (429) durante testes e uso do PWA
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["20000 per day", "5000 per hour"], # Limites relaxados para produção
    storage_uri="memory://"
)


