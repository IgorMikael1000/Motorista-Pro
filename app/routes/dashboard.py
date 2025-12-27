from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Diario, Config, Manutencao
from app.utils import safe_float, safe_money, get_config, get_brasilia_now
from app.services import calculate_dashboard, generate_week_options, get_date_range_local, get_filter_label, calculate_smart_goal
from app.services.gamification import AchievementService
from decimal import Decimal
from datetime import datetime

# Blueprint Dedicado ao Dashboard
bp = Blueprint('dashboard', __name__)

@bp.route('/', endpoint='index')
def index():
    if not current_user.is_authenticated: 
        return render_template('landing.html')
    
    # Validação de Versão para forçar refresh se necessário
    app_version = current_app.config.get('APP_VERSION')
    if current_user.last_seen_version != app_version: 
        return redirect(url_for('main.bem_vindo'))

    # Filtros de Sessão
    tipo = request.args.get('tipo')
    valor_bruto = request.args.get('valor')
    
    if not tipo: tipo = session.get('dash_tipo', 'dia')
    if not valor_bruto: valor_bruto = session.get('dash_valor')
    
    session['dash_tipo'] = tipo
    if valor_bruto: session['dash_valor'] = valor_bruto

    start_date, end_date, titulo, valor_ajustado = get_date_range_local(tipo, valor_bruto)
    filter_label = get_filter_label(tipo, start_date, end_date)
    
    # Lógica de Meta Semanal (Smart Goal)
    ask_for_goal = False
    hoje_dt = get_brasilia_now()
    if hoje_dt.weekday() == 6: # Domingo
        if get_config(current_user.id, 'meta_last_update_date') != hoje_dt.strftime('%Y-%m-%d'): 
            ask_for_goal = True

    try:
        dados = calculate_dashboard(current_user, start_date, end_date)
        meta_semanal = safe_money(get_config(current_user.id, 'meta_semanal'))
        
        lucro_raw = dados.get('lucro_semanal_acumulado', 0.0)
        lucro_semanal_acumulado = Decimal(str(lucro_raw)) if isinstance(lucro_raw, float) else lucro_raw
        
        smart_goal = calculate_smart_goal(current_user, lucro_semanal_acumulado, meta_semanal, dados['metricas'])
    except Exception as e:
        print(f"Erro Dash: {e}")
        return "Erro ao carregar dashboard.", 500

    # Gamificação: Carrega apenas o necessário para visualização
    AchievementService.get_badges_with_progress(current_user)
    
    week_options = generate_week_options(start_date.year)

    context = {
        'resumo': {'ganho': dados['ganho'], 'despesa': dados['despesa_var'], 'km': dados['km'], 'horas': dados['horas'], 'corridas': dados['total_corridas']},
        'despesas': dados['despesa_var'], 'receitas': dados['ganho'], 'lucro_operacional': dados['operacional'], 'metricas': dados['metricas'],
        'dados_apps': dados['dados_apps'], 'dados_rosca': dados['dados_rosca'], 'lista_manutencao': dados['lista_manutencao'],
        'meta': meta_semanal, 'lucro_acumulado': lucro_semanal_acumulado, 'smart_goal': smart_goal,
        'tipo': tipo, 'valor': valor_ajustado, 'filter_label': filter_label, 'week_options': week_options,
        'odo_atual': dados['odo_atual'], 'lista_despesas': dados['lista_despesas'], 'ask_for_goal': ask_for_goal
    }

    if request.headers.get('HX-Request'): 
        return render_template('partials/dashboard_content.html', **context)
        
    return render_template('index.html', **context)



