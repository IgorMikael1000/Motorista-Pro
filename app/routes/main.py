from flask import Blueprint, render_template, request, redirect, url_for, current_app, jsonify, make_response, session
from flask_login import login_required, current_user
from sqlalchemy import func, extract
from datetime import datetime, timedelta, date
from app.extensions import db
from app.models import Diario, Agendamentos, Notification, Config, Manutencao, MaintenanceLog, SupportTicket, TicketMessage
from app.utils import safe_float, safe_money, time_to_float, float_to_parts, get_config, set_config, get_brasilia_now
from app.services import get_semanas_dropdown, MESES_PT, get_maintenance_prediction, get_date_range_local, get_filter_label, generate_week_options
from app.services.gamification import AchievementService 
import calendar
from decimal import Decimal

bp = Blueprint('main', __name__)

def no_cache(view):
    from functools import wraps
    @wraps(view)
    def no_cache_view(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    return no_cache_view

@bp.route('/healthz', methods=['GET'])
def health_check(): return jsonify({'status': 'ok'}), 200

@bp.route('/manifest.json')
def manifest(): return current_app.send_static_file('manifest.json')

@bp.route('/sw.js')
def service_worker():
    response = current_app.send_static_file('sw.js')
    response.headers.add('Service-Worker-Allowed', '/')
    return response

@bp.route('/offline.html')
def offline(): return render_template('offline.html')

@bp.route('/termos', endpoint='termos')
def termos(): return render_template('termos.html')

@bp.route('/assinatura', endpoint='assinatura')
@login_required
def assinatura():
    dias = 0
    val_str = ""
    if current_user.validade:
        v = current_user.validade
        if isinstance(v, str):
            try: v = datetime.strptime(v, '%Y-%m-%d').date()
            except: pass
        if isinstance(v, datetime): 
            v = v.date()
        if isinstance(v, date):
            dias = (v - get_brasilia_now().date()).days
            val_str = v.strftime('%Y-%m-%d')
    return render_template('assinatura.html', nome=current_user.nome, validade=val_str, dias=dias, email=current_user.email)

@bp.route('/pagamento', endpoint='pagamento')
def pagamento(): return redirect(url_for('dashboard.index'))

@bp.route('/imprimir_relatorio', endpoint='imprimir_relatorio')
@login_required
def imprimir_relatorio(): return redirect(url_for('main.relatorios'))

# --- NOVA ROTA: MONITORAMENTO DINÂMICO ---
@bp.route('/monitoramento', endpoint='monitoramento')
@login_required
def monitoramento():
    # Carrega configs salvas ou usa padrão
    c_good_km = get_config(current_user.id, 'ocr_good_km', '2.0')
    c_bad_km = get_config(current_user.id, 'ocr_bad_km', '1.5')
    c_good_hour = get_config(current_user.id, 'ocr_good_hour', '60.0')
    c_bad_hour = get_config(current_user.id, 'ocr_bad_hour', '40.0')
    
    return render_template('ocr_page.html', 
                           good_km=c_good_km, bad_km=c_bad_km,
                           good_hour=c_good_hour, bad_hour=c_bad_hour)

@bp.route('/adicionar', methods=['GET','POST'], endpoint='adicionar')
@login_required
def adicionar():
    hoje_br = get_brasilia_now().strftime('%Y-%m-%d')
    custom_app_name = get_config(current_user.id, 'app_local_name', 'OUTROS')
    if request.method=='POST':
        try:
            data_obj = datetime.strptime(request.form['data'], '%Y-%m-%d').date()
            h = time_to_float(request.form.get('horas_qtd'), request.form.get('minutos_qtd'))
            g_uber = safe_money(request.form.get('ganho_uber'))
            g_99 = safe_money(request.form.get('ganho_99'))
            g_part = safe_money(request.form.get('ganho_part'))
            g_out = safe_money(request.form.get('ganho_out'))
            app_sum = g_uber + g_99 + g_part + g_out
            gb_input = safe_money(request.form.get('ganho_bruto'))
            final_gb = app_sum if app_sum > 0 else gb_input
            d_comb = safe_money(request.form.get('total_combustivel'))
            d_alim = safe_money(request.form.get('total_alimentacao'))
            d_manu = safe_money(request.form.get('total_manutencao'))
            novo = Diario(
                data=data_obj, ganho_bruto=final_gb, 
                ganho_uber=g_uber, ganho_99=g_99, ganho_part=g_part, ganho_outros=g_out, 
                despesa_combustivel=d_comb, despesa_alimentacao=d_alim, despesa_manutencao=d_manu, 
                qtd_uber=int(request.form.get('qtd_uber') or 0), qtd_99=int(request.form.get('qtd_99') or 0), 
                qtd_part=int(request.form.get('qtd_part') or 0), qtd_outros=int(request.form.get('qtd_outros') or 0), 
                km_percorrido=safe_float(request.form.get('km_percorrido')), horas_trabalhadas=h, user_id=current_user.id
            )
            db.session.add(novo); db.session.commit()
            unlocks = AchievementService.check_new_entries(current_user)
            unlock_str = ",".join(unlocks) if unlocks else ""
            return redirect(url_for('main.historico') + f"?msg=salvo&new_badges={unlock_str}")
        except Exception as e: db.session.rollback(); return f"Erro ao salvar: {e}"
    c_time = request.args.get('tempo_cronometro')
    hv=0; mv=0
    if c_time and ':' in c_time: 
        try: p = c_time.split(':'); hv, mv = int(p[0]), int(p[1]) 
        except: pass
    return render_template('adicionar.html', data_hoje=hoje_br, h_val=hv, m_val=mv, custom_app_name=custom_app_name)

@bp.route('/historico', endpoint='historico')
@login_required
@no_cache
def historico():
    page = request.args.get('page', 1, type=int)
    tipo = request.args.get('tipo', 'mes')
    valor = request.args.get('valor')
    if current_user.plan_type == 'basic' and tipo == 'anual': tipo = 'mes'; valor = None 
    start_date, end_date, _, valor_ajustado = get_date_range_local(tipo, valor)
    filter_label = get_filter_label(tipo, start_date, end_date)
    query = Diario.query.filter_by(user_id=current_user.id).filter(Diario.data >= start_date, Diario.data <= end_date)
    if current_user.plan_type == 'basic': 
        data_limite_basic = date.today() - timedelta(days=30)
        query = query.filter(Diario.data >= data_limite_basic)
    paginacao = query.order_by(Diario.data.desc()).paginate(page=page, per_page=15)
    week_options = generate_week_options(start_date.year)
    context = {'registros': [r.to_dict() for r in paginacao.items], 'page': page, 'has_next': paginacao.has_next, 'tipo': tipo, 'valor': valor_ajustado, 'filter_label': filter_label, 'week_options': week_options, 'total_pages': paginacao.pages}
    if request.headers.get('HX-Request'): return render_template('partials/history_list.html', **context)
    return render_template('historico.html', **context)

@bp.route('/editar/<int:id>', methods=('GET', 'POST'), endpoint='editar')
@login_required
@no_cache
def editar(id):
    r = Diario.query.get_or_404(id)
    if r.user_id != current_user.id: return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        try:
            r.data = datetime.strptime(request.form['data'], '%Y-%m-%d').date()
            r.km_percorrido = safe_float(request.form.get('km_percorrido'))
            r.horas_trabalhadas = time_to_float(request.form.get('horas_qtd'), request.form.get('minutos_qtd'))
            r.ganho_uber = safe_money(request.form.get('ganho_uber'))
            r.ganho_99 = safe_money(request.form.get('ganho_99'))
            r.ganho_part = safe_money(request.form.get('ganho_part'))
            r.ganho_outros = safe_money(request.form.get('ganho_outros'))
            app_sum = r.ganho_uber + r.ganho_99 + r.ganho_part + r.ganho_outros
            r.ganho_bruto = app_sum if app_sum > 0 else safe_money(request.form.get('ganho_bruto'))
            r.qtd_uber = int(request.form.get('qtd_uber') or 0)
            r.qtd_99 = int(request.form.get('qtd_99') or 0)
            r.qtd_part = int(request.form.get('qtd_part') or 0)
            r.qtd_outros = int(request.form.get('qtd_outros') or 0)
            r.despesa_combustivel = safe_money(request.form.get('despesa_combustivel'))
            r.despesa_alimentacao = safe_money(request.form.get('despesa_alimentacao'))
            r.despesa_manutencao = safe_money(request.form.get('despesa_manutencao'))
            db.session.commit()
            return redirect(url_for('main.historico'))
        except Exception as e: db.session.rollback(); return f"Erro ao editar: {e}"
    h,m = float_to_parts(r.horas_trabalhadas)
    return render_template('editar.html', registro=r.to_dict(), h_val=h, m_val=m)

@bp.route('/deletar/<int:id>', endpoint='deletar')
@login_required
def deletar(id):
    r = Diario.query.get_or_404(id)
    if r.user_id == current_user.id: db.session.delete(r); db.session.commit()
    return redirect(url_for('main.historico'))

@bp.route('/bem_vindo', endpoint='bem_vindo')
@login_required
def bem_vindo(): return render_template('bem_vindo.html', nome=current_user.nome)

@bp.route('/concluir_onboarding', methods=['POST'], endpoint='concluir_onboarding')
@login_required
def concluir_onboarding():
    try: current_user.last_seen_version = current_app.config.get('APP_VERSION'); db.session.commit(); return jsonify({'status': 'ok'})
    except Exception as e: db.session.rollback(); return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/agenda', endpoint='agenda')
@login_required
def agenda(): 
    return render_template('agenda.html', agendamentos=[x.to_dict() for x in Agendamentos.query.filter_by(user_id=current_user.id, status='pendente').order_by(Agendamentos.data_hora.asc()).all()])

@bp.route('/novo_agendamento', methods=('GET','POST'), endpoint='novo_agendamento')
@login_required
def novo_agendamento():
    if request.method == 'POST':
        try:
            dt_str = f"{request.form['data_ag']} {request.form['hora_ag']}"
            novo = Agendamentos(cliente=request.form['cliente'], data_hora=datetime.strptime(dt_str, "%Y-%m-%d %H:%M"), origem=request.form['origem'], destino=request.form['destino'], valor=safe_money(request.form['valor']), observacao=request.form['observacao'], user_id=current_user.id)
            if 'parada' in request.form: novo.parada = request.form['parada']
            db.session.add(novo); db.session.commit()
            unlocks = AchievementService.check_usage(current_user, 'agenda_add')
            return redirect(url_for('main.agenda') + f"?new_badges={','.join(unlocks) if unlocks else ''}")
        except Exception as e: db.session.rollback(); return f"Erro: {str(e)}", 500
    return render_template('novo_agendamento.html', hoje=get_brasilia_now().strftime('%Y-%m-%d'))

@bp.route('/concluir_agendamento/<int:id>', endpoint='concluir_agendamento')
@login_required
def concluir_agendamento(id):
    a = Agendamentos.query.get_or_404(id)
    if a.user_id == current_user.id:
        a.status = 'concluido'
        db.session.add(Diario(data=a.data_hora.date(), ganho_bruto=a.valor, ganho_part=a.valor, qtd_part=1, user_id=current_user.id))
        db.session.commit()
        unlocks = AchievementService.check_usage(current_user, 'agenda_concluir')
        unlock_str = ",".join(unlocks) if unlocks else ""
        if request.args.get('recibo') == '1': return redirect(url_for('settings.gerar_recibo', valor=a.valor, cliente=a.cliente, origem=a.origem, destino=a.destino, data=a.data_hora.strftime('%d/%m/%Y'), new_badges=unlock_str if unlock_str else None))
        return redirect(url_for('main.agenda') + f"?msg=concluido&new_badges={unlock_str}")
    return redirect(url_for('main.agenda') + "?msg=concluido")

@bp.route('/deletar_agendamento/<int:id>', endpoint='deletar_agendamento')
@login_required
def deletar_agendamento(id):
    a = Agendamentos.query.get_or_404(id)
    if a.user_id == current_user.id: db.session.delete(a); db.session.commit()
    return redirect(url_for('main.agenda'))

@bp.route('/update_app_name', methods=['POST'], endpoint='update_app_name')
@login_required
def update_app_name():
    if current_user.plan_type != 'premium': return jsonify({'error': 'Premium only'}), 403
    data = request.get_json()
    new_name = data.get('name', 'OUTROS').strip().upper()
    if len(new_name) > 10: new_name = new_name[:10]
    if not new_name: new_name = 'OUTROS'
    try: set_config(current_user.id, 'app_local_name', new_name); return jsonify({'status': 'ok'})
    except Exception as e: return jsonify({'error': str(e)}), 500

@bp.route('/manutencao', endpoint='manutencao')
@login_required
def manutencao():
    if not get_config(current_user.id, 'veiculo_modelo'): return redirect(url_for('settings.setup_veiculo') + "?msg=config_required")
    odo, itens = get_maintenance_prediction(current_user)
    historico_manutencao = []
    if current_user.plan_type == 'premium':
        try: historico_manutencao = MaintenanceLog.query.filter_by(user_id=current_user.id).order_by(MaintenanceLog.service_date.desc()).all()
        except: pass
    return render_template('manutencao.html', odo=odo, itens=itens, historico_manutencao=historico_manutencao)

@bp.route('/concluir_manutencao/<int:id>', endpoint='concluir_manutencao')
@login_required
def concluir_manutencao(id):
    m = Manutencao.query.get_or_404(id)
    if m.user_id == current_user.id:
        try:
            odo_sistema, _ = get_maintenance_prediction(current_user)
            km_final = odo_sistema; custo_final = Decimal('0.00')
            if current_user.plan_type == 'premium':
                km_custom = request.args.get('km_real'); custo_custom = request.args.get('custo_real')
                if km_custom: km_final = safe_float(km_custom)
                if custo_custom: custo_final = safe_money(custo_custom)
                log = MaintenanceLog(user_id=current_user.id, item_name=m.item, service_date=date.today(), service_km=km_final, cost=custo_final, notes="Concluído via Painel")
                db.session.add(log)
            db.session.delete(m); db.session.commit()
        except Exception as e: db.session.rollback(); print(f"Erro Manutencao: {e}")
    return redirect(url_for('main.manutencao'))

@bp.route('/manutencao/imprimir_historico', endpoint='imprimir_historico_manutencao')
@login_required
def imprimir_historico_manutencao():
    if current_user.plan_type != 'premium': return redirect(url_for('payments.assinar'))
    logs = MaintenanceLog.query.filter_by(user_id=current_user.id).order_by(MaintenanceLog.service_date.desc()).all()
    veiculo = {'modelo': get_config(current_user.id, 'veiculo_modelo'), 'marca': get_config(current_user.id, 'veiculo_marca'), 'ano': get_config(current_user.id, 'veiculo_ano')}
    return render_template('relatorio_manutencao_pdf.html', logs=logs, veiculo=veiculo, nome=current_user.nome, hoje=date.today().strftime('%d/%m/%Y'))

@bp.route('/adicionar_manutencao', methods=['POST'], endpoint='adicionar_manutencao')
@login_required
def adicionar_manutencao():
    try:
        kmi = safe_float(get_config(current_user.id, 'km_atual_carro'))
        total_km_all = db.session.query(db.func.sum(Diario.km_percorrido)).filter_by(user_id=current_user.id).scalar() or 0
        odo_atual = kmi + total_km_all
        intervalo = safe_float(request.form['km_proxima'])
        km_alvo = odo_atual + intervalo
        novo = Manutencao(item=request.form['item'], km_proxima=km_alvo, user_id=current_user.id)
        db.session.add(novo); db.session.commit()
        return redirect(url_for('main.manutencao'))
    except: db.session.rollback(); return redirect(url_for('main.manutencao'))

@bp.route('/editar_manutencao/<int:id>', methods=['GET', 'POST'], endpoint='editar_manutencao')
@login_required
def editar_manutencao(id):
    m = Manutencao.query.get_or_404(id)
    if m.user_id != current_user.id: return redirect(url_for('main.manutencao'))
    odo_atual, _ = get_maintenance_prediction(current_user)
    if request.method == 'POST':
        m.item = request.form['item']
        novo_alvo = safe_float(request.form['km_proxima'])
        m.km_proxima = novo_alvo
        db.session.commit()
        return redirect(url_for('main.manutencao'))
    return render_template('editar_manutencao.html', manutencao=m, odo_atual=odo_atual)

@bp.route('/editar_agendamento/<int:id>', methods=('GET', 'POST'), endpoint='editar_agendamento')
@login_required
def editar_agendamento(id):
    a = Agendamentos.query.get_or_404(id)
    if a.user_id != current_user.id: return redirect(url_for('main.agenda'))
    if request.method == 'POST':
        a.data_hora = datetime.strptime(f"{request.form['data_ag']} {request.form['hora_ag']}", "%Y-%m-%d %H:%M")
        a.cliente = request.form['cliente']; a.origem = request.form['origem']; a.destino = request.form['destino']; a.valor = safe_money(request.form['valor']); a.observacao = request.form['observacao']
        if 'parada' in request.form: a.parada = request.form['parada']
        db.session.commit(); return redirect(url_for('main.agenda'))
    return render_template('editar_agendamento.html', registro=a.to_dict(), d_val=a.data_hora.strftime('%Y-%m-%d'), h_val=a.data_hora.strftime('%H:%M'))

@bp.route('/relatorio/imprimir_pdf', endpoint='imprimir_pdf')
@login_required
def imprimir_pdf():
    if current_user.plan_type == 'basic': return redirect(url_for('payments.assinar'))
    tipo = session.get('rep_tipo', 'mes'); valor = session.get('rep_valor')
    start_date, end_date, _, titulo = get_date_range_local(tipo, valor)
    resumo = Diario.query.filter_by(user_id=current_user.id).filter(Diario.data >= start_date, Diario.data <= end_date).with_entities(func.sum(Diario.ganho_bruto), func.sum(Diario.despesa_combustivel + Diario.despesa_alimentacao + Diario.despesa_manutencao), func.sum(Diario.km_percorrido), func.sum(Diario.horas_trabalhadas), func.sum(Diario.qtd_uber + Diario.qtd_99 + Diario.qtd_part + Diario.qtd_outros), func.sum(Diario.ganho_uber), func.sum(Diario.qtd_uber), func.sum(Diario.ganho_99), func.sum(Diario.qtd_99), func.sum(Diario.ganho_part), func.sum(Diario.qtd_part), func.sum(Diario.ganho_outros), func.sum(Diario.qtd_outros)).first()
    def val(idx): return float(resumo[idx] or 0)
    ganho = val(0); despesa = val(1); km = val(2); horas = val(3); corridas = int(val(4))
    cfg = Config.query.filter_by(user_id=current_user.id).all(); c = {i.chave: i.valor for i in cfg}
    depreciacao = safe_float(c.get('depreciacao_km', 0.20)); manutencao = safe_float(c.get('manutencao_km', 0.15))
    reserva = km * (depreciacao + manutencao); lucro_real = (ganho - despesa) - reserva
    dados = {'ganho': ganho, 'despesa': despesa, 'operacional': ganho - despesa, 'lucro_real': lucro_real, 'reserva': reserva, 'km': km, 'horas': horas, 'corridas': corridas, 'media_hora': (ganho/horas) if horas > 0 else 0, 'media_km': (ganho/km) if km > 0 else 0}
    apps = {'uber_val': val(5), 'uber_qtd': int(val(6)), 'pop_val': val(7), 'pop_qtd': int(val(8)), 'part_val': val(9), 'part_qtd': int(val(10)), 'out_val': val(11), 'out_qtd': int(val(12))}
    custom_name = get_config(current_user.id, 'app_local_name', 'Outros')
    return render_template('relatorio_pdf.html', dados=dados, apps=apps, periodo=titulo, nome=current_user.nome, hoje=date.today().strftime('%d/%m/%Y'), custom_name=custom_name)

@bp.route('/relatorios', endpoint='relatorios')
@login_required
def relatorios():
    tipo = request.args.get('tipo'); valor = request.args.get('valor')
    if not tipo: tipo = session.get('rep_tipo', 'semana')
    if not valor: valor = session.get('rep_valor')
    session['rep_tipo'] = tipo; 
    if valor: session['rep_valor'] = valor
    if current_user.plan_type == 'basic' and tipo == 'anual': return redirect(url_for('main.relatorios', tipo='mes'))
    start_date, end_date, titulo, valor_ajustado = get_date_range_local(tipo, valor)
    filter_label = get_filter_label(tipo, start_date, end_date)
    registros = Diario.query.filter_by(user_id=current_user.id).filter(Diario.data >= start_date, Diario.data <= end_date).order_by(Diario.data.asc()).all()
    total_ganho = sum(r.ganho_bruto for r in registros)
    total_despesa = sum(r.despesa_combustivel + r.despesa_alimentacao + r.despesa_manutencao for r in registros)
    chart_labels = []; chart_data = []; chart_despesa = []; qtd_apps = [0, 0, 0, 0]; dados_apps = [0, 0, 0, 0]
    if tipo != 'dia':
        dados_agg = {}
        for r in registros:
            d_str = r.data.strftime('%d/%m')
            if d_str not in dados_agg: dados_agg[d_str] = {'g': 0.0, 'd': 0.0}
            dados_agg[d_str]['g'] += float(r.ganho_bruto)
            dados_agg[d_str]['d'] += float(r.despesa_combustivel + r.despesa_alimentacao + r.despesa_manutencao)
            dados_apps[0] += float(r.ganho_uber); dados_apps[1] += float(r.ganho_99); dados_apps[2] += float(r.ganho_part); dados_apps[3] += float(r.ganho_outros)
            qtd_apps[0] += int(r.qtd_uber or 0); qtd_apps[1] += int(r.qtd_99 or 0); qtd_apps[2] += int(r.qtd_part or 0); qtd_apps[3] += int(r.qtd_outros or 0)
        for k in sorted(dados_agg.keys()): chart_labels.append(k); chart_data.append(dados_agg[k]['g']); chart_despesa.append(dados_agg[k]['d'])
    best_month = {'val': 0, 'lbl': '-'}; best_week = {'val': 0, 'lbl': '-'}; best_day = {'val': 0, 'full': '-'}; best_wd = {'media': 0, 'dia': '-'}; worst_wd = {'media': 0, 'dia': '-'}
    if registros:
        rec_day = max(registros, key=lambda x: x.ganho_bruto)
        best_day = {'val': float(rec_day.ganho_bruto), 'full': rec_day.data.strftime('%d/%m/%Y')}
        wd_map = {0:'Seg', 1:'Ter', 2:'Qua', 3:'Qui', 4:'Sex', 5:'Sáb', 6:'Dom'}; wd_stats = {k: {'soma': 0, 'count': 0} for k in range(7)}
        for r in registros: wd = r.data.weekday(); wd_stats[wd]['soma'] += float(r.ganho_bruto); wd_stats[wd]['count'] += 1
        medias = [{'dia': wd_map[k], 'val': v['soma']/v['count']} for k,v in wd_stats.items() if v['count']>0]
        if medias: b_wd = max(medias, key=lambda x: x['val']); w_wd = min(medias, key=lambda x: x['val']); best_wd = {'media': b_wd['val'], 'dia': b_wd['dia']}; worst_wd = {'media': w_wd['val'], 'dia': w_wd['dia']}
        if tipo == 'anual':
            m_stats = {}
            for r in registros: m_stats[r.data.month] = m_stats.get(r.data.month, 0) + float(r.ganho_bruto)
            if m_stats: bm = max(m_stats.items(), key=lambda x: x[1]); best_month = {'val': bm[1], 'lbl': MESES_PT.get(bm[0], str(bm[0]))}
    anos = db.session.query(extract('year', Diario.data)).distinct().order_by(extract('year', Diario.data).desc()).all(); anos = [int(a[0]) for a in anos]
    custom_app_name = get_config(current_user.id, 'app_local_name', 'Outros')
    return render_template('relatorios.html', tipo=tipo, valor=valor_ajustado, titulo=titulo, chart_labels=chart_labels, chart_data=chart_data, chart_despesa=chart_despesa, total_ganho=total_ganho, total_despesa=total_despesa, best_month=best_month, best_week=best_week, best_day=best_day, best_wd=best_wd, worst_wd=worst_wd, anos=anos, semanas=[], dados_apps=dados_apps, qtd_apps=qtd_apps, filter_label=filter_label, week_options=generate_week_options(start_date.year), custom_app_name=custom_app_name)

@bp.route('/atualizar_meta', methods=['POST'], endpoint='atualizar_meta')
@login_required
def atualizar_meta():
    try: 
        set_config(current_user.id, 'meta_semanal', safe_money(request.form.get('nova_meta')))
        set_config(current_user.id, 'meta_last_update_date', get_brasilia_now().strftime('%Y-%m-%d'))
    except: pass
    return redirect(url_for('dashboard.index'))

@bp.route('/dismiss_meta', methods=['POST'], endpoint='dismiss_meta')
@login_required
def dismiss_meta():
    try: set_config(current_user.id, 'meta_last_update_date', get_brasilia_now().strftime('%Y-%m-%d'))
    except: pass
    return jsonify({'status': 'ok'})

@bp.route('/suporte', endpoint='suporte')
@login_required
def suporte(): 
    tickets = SupportTicket.query.filter_by(user_id=current_user.id).order_by(SupportTicket.updated_at.desc()).all()
    return render_template('suporte.html', tickets=tickets)

@bp.route('/suporte/novo', methods=['POST'], endpoint='suporte_novo')
@login_required
def novo_ticket():
    motivo = request.form.get('motivo'); mensagem = request.form.get('mensagem')
    if motivo and mensagem:
        ticket = SupportTicket(motivo=motivo, mensagem=mensagem, user_id=current_user.id, status='Aberto')
        db.session.add(ticket); db.session.flush() 
        db.session.add(TicketMessage(ticket_id=ticket.id, sender_type='user', message=mensagem)); db.session.commit()
    return redirect(url_for('main.suporte'))


@bp.route('/save_ocr_settings', methods=['POST'], endpoint='save_ocr_settings')
@login_required
def save_ocr_settings():
    if current_user.plan_type != 'premium': return jsonify({'error': 'Premium required'}), 403
    try:
        data = request.get_json()
        # Salva as configurações no banco
        set_config(current_user.id, 'ocr_good_km', data.get('good_km', '2.0'))
        set_config(current_user.id, 'ocr_medium_km', data.get('medium_km', '1.5'))
        set_config(current_user.id, 'ocr_good_hour', data.get('good_hour', '60.0'))
        set_config(current_user.id, 'ocr_medium_hour', data.get('medium_hour', '40.0'))
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/suporte/responder/<int:ticket_id>', methods=['POST'], endpoint='suporte_reply')
@login_required
def user_reply_ticket(ticket_id):
    ticket = SupportTicket.query.get_or_404(ticket_id)
    if ticket.user_id != current_user.id: return redirect(url_for('main.suporte'))
    mensagem = request.form.get('mensagem')
    if mensagem:
        db.session.add(TicketMessage(ticket_id=ticket.id, sender_type='user', message=mensagem))
        ticket.status = 'Em Andamento'; ticket.updated_at = datetime.now(); db.session.commit()
    return redirect(url_for('main.suporte'))