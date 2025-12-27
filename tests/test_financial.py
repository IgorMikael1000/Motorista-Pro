import pytest
from decimal import Decimal
from datetime import date
from app.utils import safe_money
from app.services import calculate_dashboard
from app.models import Diario
from app.extensions import db

def test_safe_money_conversion():
    assert safe_money("R$ 1.200,50") == Decimal('1200.50')
    assert safe_money(19.90) == Decimal('19.90')
    assert safe_money(None) == Decimal('0.00')

def test_calculo_dashboard_precisao(app, sample_user):
    d1 = Diario(user_id=sample_user.id, data=date(2025, 1, 1), ganho_bruto=Decimal('100.10'), despesa_combustivel=Decimal('33.33'))
    d2 = Diario(user_id=sample_user.id, data=date(2025, 1, 2), ganho_bruto=Decimal('50.05'), despesa_combustivel=Decimal('0.00'))
    db.session.add_all([d1, d2])
    db.session.commit()
    
    resultado = calculate_dashboard(sample_user, date(2025, 1, 1), date(2025, 1, 31))
    
    assert resultado['ganho'] == 150.15 
    assert resultado['despesa_var'] == 33.33
    assert resultado['operacional'] == 116.82



