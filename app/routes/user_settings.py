from flask import Blueprint, render_template, request, redirect, url_for, send_file, Response, flash, current_app, jsonify, session
from flask_login import login_required, current_user
from datetime import datetime, timedelta, date
import json
import calendar
import secrets
import string
from decimal import Decimal, ROUND_HALF_UP
from app.extensions import db
from app.models import Config, Manutencao, Diario, Agendamentos, SupportTicket, TicketMessage, User, Notification, Achievement, UserAchievement, CustosFixos
from app.utils import set_config, safe_float, safe_money, get_config, get_brasilia_now
from app.services import get_maintenance_prediction, get_filter_label # Importado get_filter_label
from app.services.gamification import AchievementService

bp = Blueprint('settings', __name__)

def ensure_referral_code(user):
    if not user.referral_code:
        chars = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(secrets.choice(chars) for _ in range(6))
            if not User.query.filter_by(referral_code=code).first():
                user.referral_code = code; db.session.commit(); break

def get_date_range_settings(tipo, valor):
    hoje = get_brasilia_now().date(); start = end = hoje
    if tipo == 'dia':
        if not valor: valor = hoje.strftime('%Y-%m-%d')
        try: start = end = datetime.strptime(valor, '%Y-%m-%d').date()
        except: start = end = hoje
    elif tipo == 'semana':
        try:
            if valor and '|' in valor: d1, d2 = valor.split('|'); start = datetime.strptime(d1, '%Y-%m-%d').date(); end = datetime.strptime(d2, '%Y-%m-%d').date()
            else: idx = (hoje.weekday() + 1) % 7; start = hoje - timedelta(days=idx); end = start + timedelta(days=6)
        except: start = end = hoje
    elif tipo == 'mes':
        try:
            if not valor: valor = hoje.strftime('%Y-%m')
            dt = datetime.strptime(valor + '-01', '%Y-%m-%d').date(); start = dt; end = date(dt.year, dt.month, calendar.monthrange(dt.year, dt.month)[1])
        except: start = date(hoje.year, hoje.month, 1); end = date(hoje.year, hoje.month, calendar.monthrange(hoje.year, hoje.month)[1])
    return start, end

# --- ROTAS DE DESENVOLVIMENTO ---
@bp.route('/dev/switch_basic', methods=['POST'])
@login_required
def switch_basic():
    current_user.plan_type = 'basic'
    db.session.commit()
    return redirect(url_for('settings.configuracoes'))

# --- ROTAS DE CONFIGURAÇÃO GERAL ---
@bp.route('/configuracoes', endpoint='configuracoes')
@login_required
def configuracoes():
    is_trial=False; dias=0
    try: 
        if current_user.validade: 
            cad = current_user.data_cadastro
            if isinstance(cad, str): cad = datetime.strptime(cad, '%Y-%m-%d').date()
            val = current_user.validade
            if isinstance(val, str): val = datetime.strptime(val, '%Y-%m-%d').date()
            if (val - cad).days <= 7: is_trial=True; dias = (val - get_brasilia_now().date()).days
    except: pass
    app_version = current_app.config.get('APP_VERSION', 'v3.3-Stable')
    return render_template('configuracoes.html', version=app_version, is_trial=is_trial, dias_restantes=dias)

@bp.route('/dados_pessoais', endpoint='dados_pessoais')
@login_required
def dados_pessoais(): return render_template('user_data.html')

@bp.route('/update_user_data', methods=['POST'], endpoint='update_user_data')
@login_required
def update_user_data():
    try:
        current_user.nome = request.form.get('nome'); current_user.whatsapp = request.form.get('whatsapp'); current_user.endereco = request.form.get('endereco')
        data_nasc = request.form.get('data_nascimento')
        if data_nasc: current_user.data_nascimento = datetime.strptime(data_nasc, '%Y-%m-%d').date()
        db.session.commit(); flash('Dados atualizados com sucesso!', 'success')
    except Exception as e: db.session.rollback(); flash(f'Erro ao atualizar: {str(e)}', 'error')
    return redirect(url_for('settings.dados_pessoais'))

@bp.route('/seguranca', endpoint='seguranca')
@login_required
def seguranca(): return render_template('security_settings.html')

@bp.route('/update_email', methods=['POST'], endpoint='update_email')
@login_required
def update_email():
    new_email = request.form.get('new_email')
    if User.query.filter_by(email=new_email).first(): flash('Este e-mail já está em uso.', 'error'); return redirect(url_for('settings.seguranca'))
    try: current_user.email = new_email; db.session.commit(); flash('E-mail atualizado!', 'success')
    except: db.session.rollback(); flash('Erro ao atualizar.', 'error')
    return redirect(url_for('settings.seguranca'))

@bp.route('/update_password', methods=['POST'], endpoint='update_password')
@login_required
def update_password():
    if not current_user.check_password(request.form.get('current_password')): flash('Senha atual incorreta.', 'error'); return redirect(url_for('settings.seguranca'))
    try: current_user.set_password(request.form.get('new_password')); db.session.commit(); flash('Senha alterada!', 'success')
    except: db.session.rollback(); flash('Erro ao alterar senha.', 'error')
    return redirect(url_for('settings.seguranca'))

@bp.route('/update_avatar', methods=['POST'])
@login_required
def update_avatar():
    data = request.get_json()
    if not data or 'url' not in data: return jsonify({'error': 'URL inválida'}), 400
    try: current_user.profile_image = data['url']; db.session.commit(); return jsonify({'success': True})
    except Exception as e: return jsonify({'error': str(e)}), 500

@bp.route('/indique', endpoint='indique')
@login_required
def indique():
    ensure_referral_code(current_user)
    total_indicados = User.query.filter_by(referred_by=current_user.id).count()
    total_pagos = User.query.filter_by(referred_by=current_user.id, referral_bonus_given=True).count()
    economia = total_pagos * 9.95
    ultimos = User.query.filter_by(referred_by=current_user.id).order_by(User.id.desc()).limit(10).all()
    _, unlocks = AchievementService.get_badges_with_progress(current_user)
    return render_template('indique.html', code=current_user.referral_code, total=total_indicados, ganhos=economia, ultimos=ultimos, new_badges=",".join(unlocks) if unlocks else None)

@bp.route('/conquistas', endpoint='conquistas')
@login_required
def page_conquistas():
    badges_list, new_unlocks = AchievementService.get_badges_with_progress(current_user)
    categorias = {'iniciante': [], 'habito': [], 'financeiro': [], 'ferramentas': [], 'master': []}
    for b in badges_list:
        cat = b.get('categoria', 'iniciante')
        if cat in categorias: categorias[cat].append(b)
    try:
        if new_unlocks: UserAchievement.query.filter(UserAchievement.user_id == current_user.id, UserAchievement.achievement_id.in_(new_unlocks)).update({'visto': True}, synchronize_session=False); db.session.commit()
    except: db.session.rollback()
    total_unlocked = len([b for b in badges_list if b['unlocked']])
    return render_template('conquistas.html', categorias=categorias, total_unlocked=total_unlocked, total_all=len(badges_list))

# --- IMPORTAÇÃO E EXPORTAÇÃO ---
@bp.route('/configuracoes/importar', methods=['POST'], endpoint='importar_dados')
@login_required
def importar_dados():
    if 'file' not in request.files: return redirect(url_for('settings.configuracoes') + "?msg=erro_arquivo")
    file = request.files['file']
    try:
        data = json.load(file)
        with db.session.begin_nested():
            if 'user' in data:
                u_data = data['user']
                if 'nome' in u_data: current_user.nome = u_data['nome']
                if 'whatsapp' in u_data: current_user.whatsapp = u_data['whatsapp']
            Diario.query.filter_by(user_id=current_user.id).delete(); Agendamentos.query.filter_by(user_id=current_user.id).delete(); Manutencao.query.filter_by(user_id=current_user.id).delete(); Config.query.filter_by(user_id=current_user.id).delete()
            def parse_dt(d_str):
                try: return datetime.strptime(d_str, '%Y-%m-%d').date()
                except: return None
            if 'diarios' in data:
                for d in data['diarios']:
                    d_val = parse_dt(d.get('data'))
                    db.session.add(Diario(data=d_val, ganho_bruto=safe_money(d.get('ganho_bruto')), ganho_uber=safe_money(d.get('ganho_uber')), ganho_99=safe_money(d.get('ganho_99')), ganho_part=safe_money(d.get('ganho_part')), ganho_outros=safe_money(d.get('ganho_outros')), despesa_combustivel=safe_money(d.get('despesa_combustivel')), despesa_alimentacao=safe_money(d.get('despesa_alimentacao')), despesa_manutencao=safe_money(d.get('despesa_manutencao')), qtd_uber=d.get('qtd_uber'), qtd_99=d.get('qtd_99'), qtd_part=d.get('qtd_part'), qtd_outros=d.get('qtd_outros'), km_percorrido=d.get('km_percorrido'), horas_trabalhadas=d.get('horas_trabalhadas'), user_id=current_user.id))
            if 'manutencao' in data:
                for m in data['manutencao']: db.session.add(Manutencao(item=m.get('item'), km_troca=m.get('km_troca'), km_proxima=m.get('km_proxima'), status=m.get('status'), user_id=current_user.id))
            if 'configs' in data:
                for cfg in data['configs']: db.session.add(Config(chave=cfg.get('chave'), valor=cfg.get('valor'), user_id=current_user.id))
        db.session.commit()
        return redirect(url_for('settings.configuracoes') + f"?msg=restaurado_ok")
    except: db.session.rollback(); return redirect(url_for('settings.configuracoes') + "?msg=erro_processar")

@bp.route('/exportar', endpoint='exportar_dados')
@login_required
def exportar_dados():
    data = { 'user': current_user.to_dict(), 'diarios': [d.to_dict() for d in Diario.query.filter_by(user_id=current_user.id).all()], 'manutencao': [m.to_dict() for m in Manutencao.query.filter_by(user_id=current_user.id).all()], 'configs': [c.to_dict() for c in Config.query.filter_by(user_id=current_user.id).all()] }
    if 'password_hash' in data['user']: del data['user']['password_hash']
    return Response(json.dumps(data, indent=4, ensure_ascii=False, default=str), mimetype='application/json', headers={'Content-Disposition': f'attachment;filename=backup_motoristapro_{current_user.id}.json'})

# --- NOTIFICAÇÕES ---
@bp.route('/notifications', endpoint='notifications')
@login_required
def notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    for n in notifs: n.created_at = n.created_at - timedelta(hours=3)
    return render_template('notifications.html', notifications=notifs)

@bp.route('/mark_notification/<int:id>', endpoint='mark_notification')
@login_required
def mark_notification(id):
    n = Notification.query.get_or_404(id)
    if n.user_id == current_user.id: n.is_read = True; db.session.commit()
    return redirect(url_for('settings.notifications'))

@bp.route('/mark_all_read', endpoint='mark_all_read')
@login_required
def mark_all_read():
    try: Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True}); db.session.commit()
    except: db.session.rollback()
    return redirect(url_for('settings.notifications'))

@bp.route('/clear_notifications', endpoint='clear_notifications')
@login_required
def clear_notifications():
    try: Notification.query.filter_by(user_id=current_user.id).delete(); db.session.commit()
    except: db.session.rollback()
    return redirect(url_for('settings.notifications'))

# --- CALCULADORA E SETUP ---
@bp.route('/calculadora', methods=('GET','POST'), endpoint='calculadora')
@login_required
def calculadora():
    if request.method == 'POST':
        if 'preco_km' in request.form: 
            set_config(current_user.id, 'preco_km', request.form['preco_km']); set_config(current_user.id, 'preco_min', request.form['preco_min']); set_config(current_user.id, 'taxa_base', request.form['taxa_base'])
        if 'consumo_etanol' in request.form: 
            set_config(current_user.id, 'consumo_etanol', request.form['consumo_etanol']); set_config(current_user.id, 'consumo_gasolina', request.form['consumo_gasolina'])
        return redirect(url_for('settings.calculadora'))
    cfg_list = Config.query.filter_by(user_id=current_user.id).all(); cfg = {c.chave: c.valor for c in cfg_list}
    return render_template('calculadora.html', p_km=cfg.get('preco_km'), p_min=cfg.get('preco_min'), taxa=cfg.get('taxa_base'), c_etanol=cfg.get('consumo_etanol','7'), c_gas=cfg.get('consumo_gasolina','10'))

@bp.route('/lucro_real', endpoint='lucro_real')
@login_required
def lucro_real():
    if not get_config(current_user.id, 'veiculo_modelo'): 
        return redirect(url_for('settings.setup_veiculo') + "?msg=config_required")
    
    cfg_list = Config.query.filter_by(user_id=current_user.id).all()
    cfg = {c.chave: c.valor for c in cfg_list}
    
    # Pega os parâmetros do Dashboard (via query params ou sessão)
    tipo = request.args.get('tipo', session.get('dash_tipo', 'dia'))
    valor = request.args.get('valor', session.get('dash_valor', ''))
    
    # Toggle de Custos Fixos (Default: False)
    usar_custos_fixos = request.args.get('usar_custos_fixos') == 'true'
    
    start_date, end_date = get_date_range_settings(tipo, valor)
    
    # Gera o rótulo amigável (ex: "Semana Atual")
    periodo_label = get_filter_label(tipo, start_date, end_date)
    
    registros = Diario.query.filter_by(user_id=current_user.id).filter(Diario.data >= start_date).filter(Diario.data <= end_date).all()
    
    # === CÁLCULO FINANCEIRO SEGURO (Decimal) ===
    ganho_total = sum((r.ganho_bruto or Decimal('0.00')) for r in registros)
    
    despesa_var = sum(
        (r.despesa_combustivel or Decimal('0.00')) + 
        (r.despesa_alimentacao or Decimal('0.00')) + 
        (r.despesa_manutencao or Decimal('0.00')) 
        for r in registros
    )
    
    km_total = sum((r.km_percorrido or 0.0) for r in registros)
    lucro_operacional = ganho_total - despesa_var
    
    # Configurações Variáveis
    depreciacao_km = safe_money(cfg.get('depreciacao_km', '0.20'))
    manutencao_km = safe_money(cfg.get('manutencao_km', '0.15'))
    autonomia = safe_float(cfg.get('autonomia_kml', '10'))
    preco_comb = safe_money(cfg.get('preco_combustivel', '0'))
    
    custo_fuel_km_dec = (preco_comb / Decimal(str(autonomia))) if autonomia > 0 else Decimal('0.00')
    custo_km_reserva = depreciacao_km + manutencao_km
    custo_total_rodagem = custo_fuel_km_dec + custo_km_reserva
    
    # Reserva Técnica (Variável por KM)
    total_reserva = Decimal(str(km_total)) * custo_km_reserva
    
    # === CUSTOS FIXOS (Reserva Operacional) ===
    total_custo_fixo_periodo = Decimal('0.00')
    
    if usar_custos_fixos and current_user.plan_type == 'premium':
        seguro_mensal = safe_money(cfg.get('seguro_mensal', '0'))
        ipva_anual = safe_money(cfg.get('ipva_anual', '0'))
        aluguel_semanal = safe_money(cfg.get('aluguel_semanal', '0'))
        financiamento_mensal = safe_money(cfg.get('financiamento_mensal', '0'))
        
        # Normaliza para Custo Dia
        custo_dia_seguro = seguro_mensal / 30
        custo_dia_ipva = ipva_anual / 365
        custo_dia_aluguel = aluguel_semanal / 7
        custo_dia_financ = financiamento_mensal / 30
        
        total_fixo_dia = custo_dia_seguro + custo_dia_ipva + custo_dia_aluguel + custo_dia_financ
        
        # Calcula dias no período
        num_dias = (end_date - start_date).days + 1
        total_custo_fixo_periodo = total_fixo_dia * num_dias

    lucro_real_val = lucro_operacional - total_reserva - total_custo_fixo_periodo
    
    return render_template('lucro_real.html', 
                           c=cfg, 
                           d={'custo_km_reserva': custo_km_reserva, 'custo_total_rodagem': custo_total_rodagem}, 
                           lucro_operacional=lucro_operacional, 
                           km_total=km_total, 
                           total_reserva=total_reserva, 
                           total_custo_fixo=total_custo_fixo_periodo,
                           usar_custos_fixos=usar_custos_fixos,
                           lucro_real=lucro_real_val,
                           tipo=tipo, valor=valor,
                           periodo_label=periodo_label)

@bp.route('/setup_veiculo', methods=('GET', 'POST'), endpoint='setup_veiculo')
@login_required
def setup_veiculo():
    if request.method == 'POST':
        if request.form.get('action') == 'delete':
            keys_to_delete = ['veiculo_marca', 'veiculo_modelo', 'veiculo_ano', 'autonomia_kml', 'preco_combustivel', 'depreciacao_km', 'manutencao_km', 'km_atual_carro', 'seguro_mensal', 'ipva_anual', 'aluguel_semanal', 'financiamento_mensal']
            for k in keys_to_delete:
                c = Config.query.filter_by(user_id=current_user.id, chave=k).first()
                if c: db.session.delete(c)
            db.session.commit(); return redirect(url_for('settings.lucro_real'))
        else:
            for campo in ['veiculo_marca', 'veiculo_modelo', 'veiculo_ano', 'autonomia_kml', 'preco_combustivel', 'depreciacao_km', 'manutencao_km', 'km_atual_carro']: 
                set_config(current_user.id, campo, request.form.get(campo, ''))
            
            if current_user.plan_type == 'premium':
                for campo in ['seguro_mensal', 'ipva_anual', 'aluguel_semanal', 'financiamento_mensal']:
                    set_config(current_user.id, campo, request.form.get(campo, '0'))
            
            return redirect(url_for('settings.lucro_real'))
            
    cfg_list = Config.query.filter_by(user_id=current_user.id).all(); c = {cfg.chave: cfg.valor for cfg in cfg_list}
    return render_template('setup_veiculo.html', c=c)

@bp.route('/gerar_recibo', methods=['GET', 'POST'], endpoint='gerar_recibo')
@login_required
def gerar_recibo():
    unlocks = AchievementService.check_usage(current_user, 'recibo'); agenda_badges = request.args.get('new_badges')
    if agenda_badges: unlocks.extend(agenda_badges.split(','))
    unlock_str = ",".join(unlocks) if unlocks else None
    data = { 'motorista': current_user.nome, 'valor': request.args.get('valor', '0.00'), 'cliente': request.args.get('cliente', 'Passageiro'), 'origem': request.args.get('origem', ''), 'destino': request.args.get('destino', ''), 'data': request.args.get('data', get_brasilia_now().strftime('%d/%m/%Y')) }
    return render_template('recibo.html', data=data, new_badges=unlock_str)

@bp.route('/adicionar_custo', methods=['POST'], endpoint='adicionar_custo')
@login_required
def adicionar_custo():
    try:
        nome = request.form.get('nome'); valor = safe_money(request.form.get('valor'))
        novo_custo = CustosFixos(nome=nome, valor=valor, tipo='mensal', user_id=current_user.id)
        db.session.add(novo_custo); db.session.commit()
        return redirect(url_for('settings.custos'))
    except: db.session.rollback(); return redirect(url_for('settings.custos'))

@bp.route('/deletar_custo/<int:id>', endpoint='deletar_custo')
@login_required
def deletar_custo(id):
    try:
        custo = CustosFixos.query.get_or_404(id)
        if custo.user_id == current_user.id: db.session.delete(custo); db.session.commit()
    except: db.session.rollback()
    return redirect(url_for('settings.custos'))

@bp.route('/custos', endpoint='custos')
@login_required
def custos():
    lista_custos = CustosFixos.query.filter_by(user_id=current_user.id).all()
    return render_template('custos.html', custos=lista_custos)


