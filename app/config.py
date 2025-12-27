import os

class Config:
    # --- SEGURANÇA CRÍTICA ---
    # Verifica se estamos em produção
    is_prod = os.environ.get('FLASK_ENV') == 'production' or os.environ.get('RENDER')

    # Chave secreta: Obrigatória em produção.
    # Em desenvolvimento local, usa uma chave de teste.
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        if is_prod:
            # Em produção, não podemos rodar sem chave segura
            raise ValueError("ERRO CRÍTICO: SECRET_KEY não configurada no Render!")
        else:
            SECRET_KEY = 'dev_key_apenas_para_testes_locais'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # --- ESTRATÉGIA DE PREÇOS ---
    PLANS = {
        'basic': {
            'nome': 'Motorista Basic',
            'valor': '9.90',
            'valor_display': '9,90',
            'stripe_price_id': os.environ.get('STRIPE_PRICE_BASIC', 'price_HOLDER_BASIC'),
            'desc_diario': '0,33',
            'cor': '#64748B'
        },
        'premium': {
            'nome': 'Motorista Pro (Premium)',
            'valor': '19.90',
            'valor_display': '19,90',
            'dias': 30,
            'stripe_price_id': os.environ.get('STRIPE_PRICE_ID', 'price_HOLDER_PREMIUM'),
            # ATUALIZADO: Lê o cupão do ambiente ou usa o padrão.
            # Crie este cupão na Stripe com o ID 'Ue91b9U9' ou configure STRIPE_COUPON_ID no Render.
            'stripe_coupon_id': os.environ.get('STRIPE_COUPON_ID', 'Ue91b9U9'), 
            'desc_diario': '0,66',
            'cor': '#2563EB'
        }
    }

    # --- OTIMIZAÇÃO DE MEMÓRIA DO BANCO (RENDER) ---
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 5,      
        "max_overflow": 2,    
        "pool_timeout": 30
    }

    @staticmethod
    def get_db_uri():
        # 1. Prioridade: Variável de Ambiente (Render / Codespaces configurado)
        env_url = os.environ.get('DATABASE_URL')
        
        # 2. SEU BANCO DE PRODUÇÃO (Removido do código por segurança)
        # O sistema agora confia EXCLUSIVAMENTE na variável de ambiente.
        
        if env_url:
            clean_url = env_url.strip().replace("'", "").replace('"', "")
            if clean_url.startswith("psql "): clean_url = clean_url.replace("psql ", "")
            # Fix para Render/Heroku (postgres:// -> postgresql://)
            if clean_url.startswith("postgres://"): clean_url = clean_url.replace("postgres://", "postgresql://", 1)
            
            if 'sslmode' not in clean_url and 'localhost' not in clean_url and 'sqlite' not in clean_url:
                separator = '&' if '?' in clean_url else '?'
                clean_url = f"{clean_url}{separator}sslmode=require"
            return clean_url
        else:
            # Fallback seguro: SQLite local (apenas para testes no Termux/Codespace se não houver env)
            print("AVISO: DATABASE_URL não encontrada. Usando SQLite local para testes.")
            basedir = os.path.abspath(os.path.dirname(__file__))
            return 'sqlite:///' + os.path.join(basedir, 'motorista_local.db')

    SQLALCHEMY_DATABASE_URI = get_db_uri()



