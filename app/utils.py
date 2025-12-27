import re
import logging
from functools import wraps
from flask import redirect, url_for, session
from app.extensions import db
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

# Logger
logger = logging.getLogger(__name__)

# --- TIMEZONE BRASÍLIA ---
def get_brasilia_now():
    """Retorna datetime atual em UTC-3 (Brasília)"""
    return datetime.utcnow() - timedelta(hours=3)

def to_brasilia(dt):
    """Converte um datetime UTC para Brasília (UTC-3)"""
    if not dt: return None
    if isinstance(dt, str): return dt
    return dt - timedelta(hours=3)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'): return redirect(url_for('auth.admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def safe_decimal(value):
    """
    Converte valor para Decimal (Financeiro) com alta robustez.
    """
    if value is None or value == '': 
        return Decimal('0.00')
    
    if isinstance(value, Decimal):
        return value
        
    if isinstance(value, (float, int)):
        return Decimal(str(value))

    try:
        val_str = str(value).strip().replace('R$', '').strip()
        if ',' in val_str and '.' in val_str:
            val_str = val_str.replace('.', '').replace(',', '.')
        elif ',' in val_str:
            val_str = val_str.replace(',', '.')
        return Decimal(val_str)
    except (ValueError, InvalidOperation):
        return Decimal('0.00')

def safe_money(value):
    """Retorna Decimal arredondado para 2 casas decimais (Dinheiro)."""
    d = safe_decimal(value)
    return d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def safe_float(value):
    try:
        dec = safe_decimal(value)
        return float(dec)
    except:
        return 0.0

def time_to_float(h, m):
    try: return int(h or 0) + (int(m or 0) / 60.0)
    except: return 0.0

def float_to_parts(val):
    if not val: return 0, 0
    h = int(val)
    m = int(round((val - h) * 60))
    return h, m

def get_config(user_id, key, default=''):
    from app.models import Config
    try: 
        cfg = Config.query.filter_by(user_id=user_id, chave=key).first()
        return cfg.valor if cfg else default
    except: return default

def set_config(user_id, key, val):
    from app.models import Config
    try:
        cfg = Config.query.filter_by(user_id=user_id, chave=key).first()
        if cfg: cfg.valor = str(val)
        else: db.session.add(Config(chave=key, valor=str(val), user_id=user_id))
        db.session.commit()
    except: pass

def init_user_configs(user):
    from app.models import Config
    try:
        # ATUALIZADO: Inclui financiamento
        default_configs = {
            'meta_mensal': '3000.00',
            'meta_semanal': '700.00',
            'preco_km': '2.00', 
            'preco_min': '0.20', 
            'taxa_base': '5.00', 
            'km_atual_carro': '0', 
            'veiculo_marca': '', 
            'veiculo_modelo': '', 
            'autonomia_kml': '10', 
            'preco_combustivel': '5.00', 
            'seguro_mensal': '0',
            'ipva_anual': '0',
            'aluguel_semanal': '0',
            'financiamento_mensal': '0', # Novo
            'depreciacao_km': '0.20', 
            'manutencao_km': '0.15', 
            'consumo_etanol': '7.0', 
            'consumo_gasolina': '10.0'
        }
        for k, v in default_configs.items(): 
            if not Config.query.filter_by(user_id=user.id, chave=k).first(): db.session.add(Config(chave=k, valor=v, user_id=user.id))
        db.session.commit()
    except: pass

# --- FILTROS TEMPLATE ---
def clean_phone_filter(s):
    if not s: return ""
    return re.sub(r'\D', '', str(s))

def float_to_time_filter(val):
    if not val: return "00:00"
    h = int(val)
    m = int(round((val - h) * 60))
    return f"{h:02d}:{m:02d}"



