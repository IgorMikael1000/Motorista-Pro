from sqlalchemy import func, extract, and_
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from app.extensions import db
from app.models import Diario, Config, Manutencao, MaintenanceLog, CustosFixos
from app.utils import safe_float, safe_money, get_config, get_brasilia_now
from decimal import Decimal
import calendar

# Mapeamento de meses para gráficos
MESES_PT = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}

def get_current_week_range():
    """Retorna start_date (Domingo) e end_date (Sábado) da semana atual."""
    hoje = get_brasilia_now().date()
    # Ajuste para Domingo=0: (weekday + 1) % 7
    idx_domingo = (hoje.weekday() + 1) % 7
    start = hoje - timedelta(days=idx_domingo) # Domingo
    end = start + timedelta(days=6)            # Sábado
    return start, end

def generate_week_options(year):
    """Gera lista de semanas para o dropdown (Domingo a Sábado)."""
    hoje = get_brasilia_now().date()
    try:
        d = date(year, 1, 1)
        idx_domingo = (d.weekday() + 1) % 7
        start_week_1 = d - timedelta(days=idx_domingo)
        
        d = start_week_1
        weeks = []
        
        while d.year == year or (d + timedelta(days=6)).year == year:
            start_date = d
            end_date = d + timedelta(days=6)
            label = f"{start_date.strftime('%d/%m')} - {end_date.strftime('%d/%m')}"
            weeks.append({'value': start_date.strftime('%Y-%m-%d'), 'label': label})
            d += timedelta(weeks=1)
            if d.year > year + 1: break
        
        current_start, _ = get_current_week_range()
        
        if year == hoje.year:
            # Adiciona opção de destaque "Esta Semana"
            weeks.insert(0, {
                'value': current_start.strftime('%Y-%m-%d'), 
                'label': f"ESTA SEMANA: {current_start.strftime('%d/%m')} - {(current_start + timedelta(days=6)).strftime('%d/%m')}"
            })
            
            # Remove duplicatas
            seen = set()
            unique_weeks = []
            for w in weeks:
                if w['value'] not in seen:
                    unique_weeks.append(w)
                    seen.add(w['value'])
            return unique_weeks
            
        return weeks
    except Exception as e:
        print(f"Erro generate_week_options: {e}")
        return []

# --- FUNÇÃO DE COMPATIBILIDADE (CRÍTICA PARA EVITAR ERRO) ---
def get_semanas_dropdown(year):
    return generate_week_options(year)

def get_filter_label(tipo, start, end):
    if tipo == 'dia': return start.strftime('%d/%m/%Y')
    elif tipo == 'semana': return f"{start.strftime('%d/%m')} - {end.strftime('%d/%m')}"
    elif tipo == 'mes': return f"{MESES_PT.get(start.month, '')[:3]}/{start.year}"
    elif tipo == 'anual': return f"{start.year}"
    return "Período"

def get_date_range_local(tipo, valor):
    hoje_dt = get_brasilia_now()
    hoje = hoje_dt.date()
    start_date = end_date = hoje
    valor_ajustado = valor
    titulo = ""

    if tipo == 'dia':
        if not valor: valor = hoje.strftime('%Y-%m-%d')
        try: start_date = end_date = datetime.strptime(valor, '%Y-%m-%d').date()
        except: start_date = end_date = hoje
        valor_ajustado = start_date.strftime('%Y-%m-%d')
        titulo = start_date.strftime('%d/%m')
    
    elif tipo == 'semana':
        try:
            if valor:
                ref_date = datetime.strptime(valor, '%Y-%m-%d').date()
                start_date = ref_date
                end_date = start_date + timedelta(days=6)
            else:
                start_date, end_date = get_current_week_range()
            valor_ajustado = start_date.strftime('%Y-%m-%d')
            titulo = f"{start_date.strftime('%d/%m')} a {end_date.strftime('%d/%m')}"
        except:
            start_date, end_date = get_current_week_range()
            valor_ajustado = start_date.strftime('%Y-%m-%d')

    elif tipo == 'mes':
        try:
            if not valor: valor = hoje.strftime('%Y-%m')
            dt = datetime.strptime(valor + '-01', '%Y-%m-%d').date()
            start_date = dt
            end_date = date(dt.year, dt.month, calendar.monthrange(dt.year, dt.month)[1])
            valor_ajustado = valor
            titulo = MESES_PT.get(start_date.month, str(start_date.month))
        except:
            start_date = date(hoje.year, hoje.month, 1)
            end_date = date(hoje.year, hoje.month, calendar.monthrange(hoje.year, hoje.month)[1])
            valor_ajustado = hoje.strftime('%Y-%m')
        
    elif tipo == 'anual':
        try:
            if not valor: valor = str(hoje.year)
            ano = int(valor)
            start_date = date(ano, 1, 1)
            end_date = date(ano, 12, 31)
            valor_ajustado = str(ano)
            titulo = f"Ano {ano}"
        except:
            start_date = date(hoje.year, 1, 1)
            end_date = date(hoje.year, 12, 31)
            valor_ajustado = str(hoje.year)
        
    return start_date, end_date, titulo, valor_ajustado

def get_maintenance_prediction(user):
    try:
        km_inicial = safe_float(get_config(user.id, 'km_atual_carro'))
        km_rodado_total = db.session.query(func.sum(Diario.km_percorrido)).filter_by(user_id=user.id).scalar() or 0.0
        odo_atual = km_inicial + km_rodado_total

        hoje = get_brasilia_now().date()
        data_30_dias = hoje - timedelta(days=30)
        km_30_dias = db.session.query(func.sum(Diario.km_percorrido)).filter(Diario.user_id == user.id, Diario.data >= data_30_dias).scalar() or 0.0
        media_km_dia = float(km_30_dias) / 30.0

        itens = Manutencao.query.filter_by(user_id=user.id).all()
        resultado = []

        for i in itens:
            km_alvo = float(i.km_proxima)
            falta = km_alvo - odo_atual
            
            if falta <= 0: urgencia = 'critica'; previsao_txt = "VENCIDO!"
            elif falta < 500: urgencia = 'alta'; previsao_txt = "Esta Semana"
            elif falta < 1500: urgencia = 'media'; previsao_txt = "Em Breve"
            else: urgencia = 'baixa'; previsao_txt = "Tranquilo"

            if falta > 0 and media_km_dia > 10:
                dias_restantes = int(falta / media_km_dia)
                data_prevista = hoje + timedelta(days=dias_restantes)
                previsao_txt = data_prevista.strftime('%d/%m/%Y')
            elif falta > 0: previsao_txt = "Calculando..."

            resultado.append({'id': i.id, 'item': i.item, 'km_proxima': km_alvo, 'falta_km': falta, 'urgencia': urgencia, 'previsao_txt': previsao_txt})

        resultado.sort(key=lambda x: x['falta_km'])
        return odo_atual, resultado
    except Exception as e:
        print(f"Erro Manutencao Service: {e}")
        return 0.0, []

def calculate_dashboard(user, start_date, end_date):
    ganho = Decimal('0.00'); despesa_var = Decimal('0.00'); operacional = Decimal('0.00')
    km = 0.0; horas = 0.0
    metricas = {'ganho_km': 0, 'ganho_h': 0, 'ganho_corr': 0, 'ganho_dia': 0, 'lucro_km': 0, 'lucro_h': 0, 'lucro_corr': 0, 'lucro_dia': 0}
    dados_apps = [0,0,0,0]; lista_despesas = []; dados_rosca = []
    
    resumo_db = Diario.query.filter_by(user_id=user.id).filter(Diario.data >= start_date, Diario.data <= end_date).with_entities(
        func.sum(Diario.ganho_bruto), func.sum(Diario.despesa_combustivel), func.sum(Diario.despesa_alimentacao), func.sum(Diario.despesa_manutencao), 
        func.sum(Diario.km_percorrido), func.sum(Diario.horas_trabalhadas), func.sum(Diario.ganho_uber), func.sum(Diario.ganho_99), 
        func.sum(Diario.ganho_part), func.sum(Diario.ganho_outros), func.sum(Diario.qtd_uber), func.sum(Diario.qtd_99), 
        func.sum(Diario.qtd_part), func.sum(Diario.qtd_outros), func.count(Diario.id)
    ).first()

    total_corridas = 0; dias_trabalhados = 0

    if resumo_db and resumo_db[0] is not None:
        to_dec = lambda v: Decimal(str(v)) if v is not None else Decimal('0.00')
        ganho = to_dec(resumo_db[0])
        d_comb = to_dec(resumo_db[1]); d_alim = to_dec(resumo_db[2]); d_manu = to_dec(resumo_db[3])
        km = float(resumo_db[4] or 0.0); horas = float(resumo_db[5] or 0.0)
        
        g_uber = to_dec(resumo_db[6]); g_99 = to_dec(resumo_db[7]); g_part = to_dec(resumo_db[8]); g_out = to_dec(resumo_db[9])
        q_uber = int(resumo_db[10] or 0); q_99 = int(resumo_db[11] or 0); q_part = int(resumo_db[12] or 0); q_out = int(resumo_db[13] or 0)
        dias_trabalhados = int(resumo_db[14] or 0)
        
        despesa_var = d_comb + d_alim + d_manu; operacional = ganho - despesa_var
        dados_apps = [float(g_uber), float(g_99), float(g_part), float(g_out)]
        total_corridas = q_uber + q_99 + q_part + q_out
        
        if km > 0: metricas['ganho_km'] = float(ganho)/km; metricas['lucro_km'] = float(operacional)/km
        if horas > 0: metricas['ganho_h'] = float(ganho)/horas; metricas['lucro_h'] = float(operacional)/horas
        if total_corridas > 0: metricas['ganho_corr'] = float(ganho)/total_corridas; metricas['lucro_corr'] = float(operacional)/total_corridas
        if dias_trabalhados > 0: metricas['ganho_dia'] = float(ganho)/dias_trabalhados; metricas['lucro_dia'] = float(operacional)/dias_trabalhados
        
        lista_despesas = [{'nome':'Combustível','valor':float(d_comb),'cor':'#FFC107'}, {'nome':'Alimentação','valor':float(d_alim),'cor':'#FF5722'}, {'nome':'Manutenção','valor':float(d_manu),'cor':'#9E9E9E'}]
        dados_rosca = [d['valor'] for d in lista_despesas]
    
    soma_apps = {'Uber': 0, '99': 0, 'Particular': 0, 'Outros': 0}
    if resumo_db and resumo_db[6] is not None:
         soma_apps['Uber'] = resumo_db[6] or 0; soma_apps['99'] = resumo_db[7] or 0; soma_apps['Particular'] = resumo_db[8] or 0; soma_apps['Outros'] = resumo_db[9] or 0

    domingo_atual, sabado_atual = get_current_week_range()
    acumulado_semanal_db = db.session.query(func.sum(Diario.ganho_bruto) - func.sum(func.coalesce(Diario.despesa_combustivel, 0) + func.coalesce(Diario.despesa_alimentacao, 0) + func.coalesce(Diario.despesa_manutencao, 0))).filter(Diario.user_id == user.id, Diario.data >= domingo_atual, Diario.data <= sabado_atual).scalar()
    lucro_semanal_acumulado = Decimal(str(acumulado_semanal_db)) if acumulado_semanal_db else Decimal('0.00')

    odo_atual, lista_manutencao = get_maintenance_prediction(user)
    lista_manutencao_dash = lista_manutencao[:3]

    return {'ganho': float(ganho), 'despesa_var': float(despesa_var), 'km': km, 'horas': horas, 'operacional': float(operacional), 'total_corridas': total_corridas, 'metricas': metricas, 'dados_apps': soma_apps, 'lista_despesas': lista_despesas, 'dados_rosca': dados_rosca, 'lucro_semanal_acumulado': float(lucro_semanal_acumulado), 'odo_atual': odo_atual, 'lista_manutencao': lista_manutencao_dash}

def calculate_smart_goal(user, lucro_acumulado, meta_semanal, metricas):
    meta_semanal = float(meta_semanal)
    if meta_semanal <= 0: return {'status': 'sem_meta', 'msg': 'Defina sua meta semanal!'}
    
    hoje = get_brasilia_now().date()
    ganho_hoje_res = db.session.query(func.sum(Diario.ganho_bruto), func.sum(Diario.despesa_combustivel + Diario.despesa_alimentacao + Diario.despesa_manutencao)).filter_by(user_id=user.id, data=hoje).first()
    gh = float(ganho_hoje_res[0] or 0); dh = float(ganho_hoje_res[1] or 0); lucro_hoje = gh - dh
    
    acumulado_total = float(lucro_acumulado)
    acumulado_anterior = acumulado_total - lucro_hoje 
    saldo_restante_inicio_dia = meta_semanal - acumulado_anterior
    
    if saldo_restante_inicio_dia <= 0: return {'status': 'superavit', 'msg': f"🏆 Meta semanal já batida! Tudo hoje é lucro extra.", 'hoje': lucro_hoje, 'meta_hoje': 0}

    idx_dia = (hoje.weekday() + 1) % 7; dias_restantes = 7 - idx_dia 
    if dias_restantes <= 0: dias_restantes = 1
    
    meta_do_dia = saldo_restante_inicio_dia / dias_restantes
    diff = lucro_hoje - meta_do_dia
    
    if diff >= 0:
        if diff > (meta_do_dia * 0.1): msg = f"🚀 Incrível! Superou a meta líquida de hoje em R$ {diff:.0f}."
        else: msg = f"✅ Parabéns! Meta líquida do dia batida."
        status = 'concluido'
    else:
        falta = abs(diff)
        msg = f"🎯 Meta líquida de hoje: R$ {meta_do_dia:.0f}. Faltam R$ {falta:.0f} de lucro."
        status = 'pendente'

    return {'status': status, 'msg': msg, 'meta_hoje': meta_do_dia, 'hoje': lucro_hoje, 'falta_hoje': abs(diff) if diff < 0 else 0}



