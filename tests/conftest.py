import pytest
from app import create_app
from app.extensions import db
from app.models import User
from config import Config

# Cria uma configuração específica para testes
class TestConfig(Config):
    TESTING = True
    # Usa SQLite em memória (muito rápido e não afeta o banco real)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # --- CORREÇÃO DO ERRO ---
    # Zera as configurações de pool do Postgres, pois o SQLite não suporta
    SQLALCHEMY_ENGINE_OPTIONS = {}
    
    # Desabilita proteção CSRF nos testes para facilitar
    WTF_CSRF_ENABLED = False
    # Desabilita limitação de taxa (Rate Limit) nos testes
    RATELIMIT_ENABLED = False

@pytest.fixture(scope='module')
def app():
    """Cria a instância da aplicação Flask para o teste."""
    app = create_app(TestConfig)
    
    # Cria o contexto da aplicação
    with app.app_context():
        yield app

@pytest.fixture(scope='module')
def test_client(app):
    """Cria um cliente HTTP simulado."""
    return app.test_client()

@pytest.fixture(scope='function')
def init_database(app):
    """
    Cria o banco de dados e as tabelas para cada teste.
    Depois do teste, apaga tudo.
    """
    db.create_all()
    
    # Cria um usuário de teste padrão
    user = User(
        email='teste@motorista.pro', 
        nome='Tester', 
        password_hash='fakehash',
        category='subscriber',
        is_confirmed=True
    )
    db.session.add(user)
    db.session.commit()
    
    yield db  # Roda o teste aqui
    
    db.session.remove()
    db.drop_all()

@pytest.fixture(scope='function')
def sample_user(init_database):
    """Retorna o usuário de teste já criado no banco."""
    return User.query.first()



