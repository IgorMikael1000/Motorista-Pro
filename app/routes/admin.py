import io
import csv
import zipfile
import secrets
import string
import os
import sys
import re
from datetime import datetime, timedelta, date
from flask import Blueprint, render_template, request, redirect, url_for, session, send_file, Response, current_app, flash
from werkzeug.datastructures import FileStorage
from app.utils import admin_required
from app.extensions import db
from app.models import User, Diario, Agendamentos, Manutencao, Config, SupportTicket, TicketMessage, Notification
from sqlalchemy import func, case, desc, distinct
import firebase_admin
from firebase_admin import auth as firebase_auth

try:
    import pytest
except ImportError:
    pytest = None

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/', endpoint='root')
def admin_root(): return redirect(url_for('admin.dashboard'))

@bp.route('/dashboard', endpoint='dashboard')
@admin_required
def admin_dashboard():
    try:
        filtro = request.args.get('filtro')
        query = User.query
        hoje = datetime.now().date()
        hoje_str = hoje.strftime('%Y-%m-%d')

        # Filtros básicos de SQL
        if filtro == 'trial': 
            query = query.filter(User.category == 'trial', User.validade >= hoje_str)
        elif filtro == 'subscriber': 
            query = query.filter(User.category == 'subscriber', User.validade >= hoje_str)
        elif filtro == 'expired': 
            query = query.filter((User.validade < hoje_str) | (User.category == 'expired'))
            
        raw_users = query.order_by(User.id.desc()).limit(100).all()
        
        # Totais Gerais (Otimizados com COUNT)
        total_users = db.session.query(func.count(User.id)).scalar()
        
        total_subs = db.session.query(func.count(User.id)).filter(
            User.category == 'subscriber', 
            User.validade >= hoje_str
        ).scalar()
        
        total_trial = db.session.query(func.count(User.id)).filter(
            User.category == 'trial', 
            User.validade >= hoje_str
        ).scalar()
        
        total_expired = db.session.query(func.count(User.id)).filter(
            (User.validade < hoje_str) | (User.category == 'expired')
        ).scalar()
        
        stats = { 'total': total_users, 'ativos': total_subs, 'trial': total_trial, 'vencidos': total_expired }
        users_processed = []
        
        for u in raw_users:
            try:
                dias_rest = -999
                val = None
                if u.validade:
                    if isinstance(u.validade, str):
                        try: val = datetime.strptime(u.validade, '%Y-%m-%d').date()
                        except: val = None
                    elif isinstance(u.validade, (date, datetime)): val = u.validade
                if val:
                    d_val = val.date() if isinstance(val, datetime) else val
                    dias_rest = (d_val - hoje).days
                
                label_class = 'text-expired'
                if dias_rest >= 0:
                    if u.category == 'subscriber': label_class = 'text-subscriber'
                    elif u.category == 'trial': label_class = 'text-trial'
                
                users_processed.append({
                    'id': u.id, 
                    'nome': u.nome, 
                    'email': u.email, 
                    'whatsapp': u.whatsapp, 
                    'validade': u.validade, 
                    'category': u.category, 
                    'label_class': label_class, 
                    'dias_restantes': dias_rest, 
                    'payment_method': u.payment_method,
                    'plan_type': u.plan_type
                })
            except: 
                users_processed.append({'id': u.id, 'nome': u.nome or 'Erro', 'email': u.email, 'validade': '-', 'category': 'erro', 'label_class': 'text-expired', 'dias_restantes': 0, 'payment_method': 'erro', 'plan_type': 'unknown'})
            
        return render_template('admin.html', users=users_processed, stats=stats, filtro_atual=filtro)
    except Exception as e: return f"Erro Dashboard: {str(e)}"

# --- BUSINESS INTELLIGENCE (BI) OTIMIZADO v7.0 ---
@bp.route('/business', endpoint='business')
@admin_required
def admin_business():
    # 1. Métricas Gerais (Usando agregadores SQL)
    metrics = db.session.query(
        func.sum(Diario.ganho_bruto),
        func.sum(Diario.km_percorrido),
        func.sum(Diario.despesa_combustivel + Diario.despesa_manutencao)
    ).first()
    
    total_faturamento_app = metrics[0] or 0
    total_km_rodados = metrics[1] or 1
    total_despesas = metrics[2] or 0
    
    media_reais_km = float(total_faturamento_app) / float(total_km_rodados)
    custo_medio_km = float(total_despesas) / float(total_km_rodados)

    # 2. Análise de Assinantes (Otimizada)
    hoje = datetime.now().date()
    hoje_str = hoje.strftime('%Y-%m-%d')

    # Subquery para contar tipos de plano diretamente no banco
    subs_stats = db.session.query(
        User.plan_type,
        User.payment_method,
        User.referral_balance,
        func.count(User.id)
    ).filter(
        User.category == 'subscriber', 
        User.validade >= hoje_str
    ).group_by(User.plan_type, User.payment_method, User.referral_balance).all()
    
    count_basic = 0
    count_premium = 0
    mrr_basic_bruto = 0.0
    mrr_premium_bruto = 0.0
    subs_card = 0
    subs_pix = 0
    
    PRICE_BASIC = 9.90
    PRICE_PREMIUM = 19.90

    # Itera sobre os GRUPOS, não sobre os usuários individuais (Escala infinita)
    for plano, metodo, saldo_ref, qtd in subs_stats:
        # Método
        if metodo == 'card': subs_card += qtd
        else: subs_pix += qtd
        
        # Valor base
        valor_base = PRICE_BASIC if plano == 'basic' else PRICE_PREMIUM
        
        # Desconto
        valor_final = (valor_base / 2) if saldo_ref > 0 else valor_base
        
        if plano == 'basic':
            count_basic += qtd
            mrr_basic_bruto += (valor_final * qtd)
        else:
            count_premium += qtd
            mrr_premium_bruto += (valor_final * qtd)

    # 3. Cálculo de Taxas
    TAXA_MEDIA = 0.04 
    mrr_basic_liq = mrr_basic_bruto * (1 - TAXA_MEDIA)
    mrr_premium_liq = mrr_premium_bruto * (1 - TAXA_MEDIA)
    mrr_total_liquido = mrr_basic_liq + mrr_premium_liq
    arr_projetado = mrr_total_liquido * 12

    # 4. Métricas de Engajamento
    dau = db.session.query(func.count(distinct(Diario.user_id))).filter(Diario.data == hoje).scalar() or 0
    mau = db.session.query(func.count(distinct(Diario.user_id))).filter(Diario.data >= (hoje - timedelta(days=30))).scalar() or 1
    stickiness = (dau / mau) * 100

    # LTV
    total_active = count_basic + count_premium
    ticket_medio = (mrr_total_liquido / total_active) if total_active > 0 else 0
    ltv = ticket_medio * 6 

    # Risco de Churn (Simplificado para performance)
    data_limite_risco = hoje - timedelta(days=7)
    # Subquery para pegar última atividade de cada usuário
    last_seen = db.session.query(
        Diario.user_id, 
        func.max(Diario.data).label('max_date')
    ).group_by(Diario.user_id).subquery()
    
    # Usuários ativos que não têm diário recente ou nunca tiveram
    qtd_risco = db.session.query(func.count(User.id)).outerjoin(
        last_seen, User.id == last_seen.c.user_id
    ).filter(
        User.category == 'subscriber',
        (last_seen.c.max_date < data_limite_risco) | (last_seen.c.max_date == None)
    ).scalar() or 0

    top_users = db.session.query(User.nome, User.email, func.sum(Diario.ganho_bruto).label('total_ganho'), func.count(Diario.id).label('dias_uso')).join(Diario).group_by(User.id).order_by(desc('total_ganho')).limit(5).all()

    share = db.session.query(func.sum(Diario.ganho_uber), func.sum(Diario.ganho_99), func.sum(Diario.ganho_part), func.sum(Diario.ganho_outros)).first()
    share_data = [float(x or 0) for x in share] if share else [0,0,0,0]

    # Crescimento (últimos 15 dias)
    chart_growth_data = {}
    users_last_15 = db.session.query(
        func.date(User.data_cadastro), 
        func.count(User.id)
    ).filter(User.data_cadastro >= (hoje - timedelta(days=15)))\
     .group_by(func.date(User.data_cadastro)).all()
     
    # Popula o dicionário
    map_growth = {str(d): c for d, c in users_last_15}
    
    labels_growth = []
    values_growth = []
    for i in range(15, -1, -1):
        d_obj = hoje - timedelta(days=i)
        d_str = d_obj.strftime('%Y-%m-%d')
        d_lbl = d_obj.strftime('%d/%m')
        labels_growth.append(d_lbl)
        values_growth.append(map_growth.get(d_str, 0))

    return render_template('admin_business.html', 
                           mrr_liquido=mrr_total_liquido,
                           mrr_basic=mrr_basic_liq,
                           mrr_premium=mrr_premium_liq,
                           count_basic=count_basic,
                           count_premium=count_premium,
                           arr=arr_projetado, 
                           qtd_risco=qtd_risco, 
                           media_reais_km=media_reais_km, 
                           custo_medio_km=custo_medio_km, 
                           stickiness=stickiness, 
                           ltv=ltv, 
                           subs_card=subs_card, 
                           subs_pix=subs_pix,
                           share_data=share_data, 
                           top_users=top_users, 
                           growth_labels=labels_growth, 
                           growth_values=values_growth)

@bp.route('/rodar_testes', endpoint='rodar_testes')
@admin_required
def admin_run_tests():
    if not pytest: return render_template('admin_tests.html', output="Pytest não instalado.", status="erro")
    buffer = io.StringIO(); old_stdout = sys.stdout; sys.stdout = buffer
    try:
        if os.getcwd() not in sys.path: sys.path.insert(0, os.getcwd())
        exit_code = pytest.main(["-v", "-p", "no:cacheprovider", "tests/"])
    except Exception as e: print(f"Erro: {e}")
    finally: sys.stdout = old_stdout
    output = buffer.getvalue()
    clean_output = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])').sub('', output)
    status = "sucesso" if "failed" not in clean_output.lower() and "error" not in clean_output.lower() else "erro"
    return render_template('admin_tests.html', output=clean_output, status=status)

@bp.route('/renovar/<int:user_id>', methods=['POST'], endpoint='renovar')
@admin_required
def admin_renovar_post(user_id):
    user = User.query.get_or_404(user_id)
    try: dias = int(request.form.get('dias', 30))
    except: dias = 30
    hoje = datetime.now().date(); base = hoje
    if user.validade:
        val_atual = user.validade
        if isinstance(val_atual, str):
            try: val_atual = datetime.strptime(val_atual, '%Y-%m-%d').date()
            except: val_atual = hoje
        elif isinstance(val_atual, datetime): val_atual = val_atual.date()
        if val_atual > hoje: base = val_atual
    if dias == 1: user.data_cadastro = (datetime.now() - timedelta(days=31)).date(); user.validade = (base + timedelta(days=1))
    else: user.validade = (base + timedelta(days=dias))
    user.category = 'subscriber'; user.payment_method = 'manual'; db.session.commit()
    return redirect(url_for('admin.dashboard'))

@bp.route('/set_category/<int:user_id>/<category>', endpoint='set_category')
@admin_required
def set_category(user_id, category):
    if category not in ['trial', 'subscriber', 'expired']: return "Invalido"
    user = User.query.get_or_404(user_id); user.category = category; db.session.commit()
    return redirect(url_for('admin.dashboard'))

@bp.route('/backup/global', endpoint='backup_global')
@admin_required
def admin_backup_global():
    try:
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            def add_model_to_zip(filename, model_class):
                query = model_class.query
                if hasattr(query, 'yield_per'): items = query.yield_per(1000)
                else: items = query.all()
                columns = [c.name for c in model_class.__table__.columns]
                si = io.StringIO(); cw = csv.writer(si); cw.writerow(columns)
                if items:
                    for item in items:
                        row = [str(getattr(item, c)) if getattr(item, c) is not None else '' for c in columns]
                        cw.writerow(row)
                zf.writestr(filename, si.getvalue())
            add_model_to_zip('users.csv', User); add_model_to_zip('diarios.csv', Diario); add_model_to_zip('agendamentos.csv', Agendamentos); add_model_to_zip('manutencao.csv', Manutencao); add_model_to_zip('configs.csv', Config); add_model_to_zip('tickets.csv', SupportTicket); add_model_to_zip('tickets_msg.csv', TicketMessage)
        memory_file.seek(0); timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        return send_file(memory_file, download_name=f'backup_full_{timestamp}.zip', as_attachment=True, mimetype='application/zip')
    except Exception as e: return f"Erro: {e}", 500

@bp.route('/restore/global', methods=['POST'], endpoint='restore_global')
@admin_required
def admin_restore_global():
    if 'file' not in request.files: return "Erro", 400
    file = request.files['file']
    try:
        with zipfile.ZipFile(io.BytesIO(file.read())) as zf:
            map_files = [('users.csv', User), ('configs.csv', Config), ('manutencao.csv', Manutencao), ('agendamentos.csv', Agendamentos), ('diarios.csv', Diario), ('tickets.csv', SupportTicket), ('tickets_msg.csv', TicketMessage)]
            for filename, model_class in map_files:
                if filename in zf.namelist():
                    with zf.open(filename) as f:
                        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))
                        for row in reader:
                            data = {k: (None if v=='' else True if v.lower()=='true' else False if v.lower()=='false' else v) for k,v in row.items()}
                            target = model_class.query.get(data['id']) if data.get('id') else None
                            if not target:
                                if model_class==User and data.get('email'): target=User.query.filter_by(email=data['email']).first()
                                elif model_class==Config and data.get('user_id'): target=Config.query.filter_by(user_id=data['user_id'], chave=data.get('chave')).first()
                            if target:
                                for k,v in data.items(): 
                                    if hasattr(target, k) and k!='id': setattr(target, k, v)
                            else:
                                try: db.session.add(model_class(**{k:v for k,v in data.items() if hasattr(model_class, k)}))
                                except: pass
            db.session.commit()
        return redirect(url_for('admin.dashboard'))
    except Exception as e: db.session.rollback(); return f"Erro: {e}", 500

@bp.route('/zerar/<int:user_id>', methods=['POST'], endpoint='zerar')
@admin_required
def admin_zerar(user_id):
    u = User.query.get_or_404(user_id); u.validade = (datetime.now()-timedelta(days=1)).date(); u.category='expired'; db.session.commit(); return redirect(url_for('admin.dashboard'))

@bp.route('/temp_password/<int:user_id>', methods=['POST'], endpoint='temp_password')
@admin_required
def admin_temp_password(user_id):
    u = User.query.get_or_404(user_id); pw = ''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(6)); u.set_password(pw); u.is_temp_password=True; db.session.commit(); return f"Senha: {pw}"

@bp.route('/notify', methods=['POST'], endpoint='notify')
@admin_required
def admin_notify():
    msg = request.form.get('mensagem')
    target = request.form.get('user_id')
    if target and target.strip():
        u = User.query.get(int(target))
        if u: db.session.add(Notification(message=msg, user_id=u.id))
    else:
        # Otimização: Bulk Insert
        users = db.session.query(User.id).all()
        bulk_notifs = [{'message': msg, 'user_id': uid[0], 'is_read': False, 'created_at': datetime.now()} for uid in users]
        db.session.bulk_insert_mappings(Notification, bulk_notifs)
    db.session.commit()
    return redirect(url_for('admin.dashboard'))

@bp.route('/deletar/<int:user_id>', endpoint='deletar')
@admin_required
def admin_delete(user_id):
    u = User.query.get_or_404(user_id)
    try: firebase_auth.delete_user(firebase_auth.get_user_by_email(u.email).uid)
    except: pass
    for m in [Config, Diario, Agendamentos, Manutencao, Notification, SupportTicket]: m.query.filter_by(user_id=u.id).delete()
    db.session.delete(u); db.session.commit(); return redirect(url_for('admin.dashboard'))

@bp.route('/logout', endpoint='logout')
def admin_logout(): session.pop('is_admin', None); return redirect(url_for('auth.login'))

@bp.route('/suporte', endpoint='suporte')
@admin_required
def admin_suporte():
    tickets = db.session.query(SupportTicket, User).join(User, SupportTicket.user_id==User.id).order_by(SupportTicket.updated_at.desc()).limit(50).all()
    return render_template('admin_suporte.html', tickets=tickets)

@bp.route('/suporte/responder/<int:ticket_id>', methods=['POST'], endpoint='suporte_reply')
@admin_required
def admin_reply_ticket(ticket_id):
    t = SupportTicket.query.get_or_404(ticket_id); msg = request.form.get('mensagem')
    if msg:
        db.session.add(TicketMessage(ticket_id=t.id, sender_type='admin', message=msg)); t.status='Respondido'; t.updated_at=datetime.now(); db.session.add(Notification(user_id=t.user_id, message=f"Resp: {t.motivo}")); db.session.commit()
    return redirect(url_for('admin.suporte'))

@bp.route('/suporte/encerrar/<int:ticket_id>', endpoint='suporte_close')
@admin_required
def admin_close_ticket(ticket_id):
    t = SupportTicket.query.get_or_404(ticket_id); t.status='Encerrado'; t.updated_at=datetime.now(); db.session.commit(); return redirect(url_for('admin.suporte'))

@bp.route('/suporte/limpar_historico', endpoint='suporte_clear')
@admin_required
def admin_clear_closed_tickets():
    try:
        tickets = SupportTicket.query.filter((SupportTicket.status=='Encerrado')|(SupportTicket.status=='Solucionado')).all()
        for t in tickets: db.session.delete(t)
        db.session.commit()
    except: db.session.rollback()
    return redirect(url_for('admin.suporte'))


