import os
import stripe
import mercadopago
from datetime import datetime, timedelta
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from app.extensions import db, csrf
from app.models import User, Notification

bp = Blueprint('payments', __name__)

# Configuração das Chaves (Lê do ambiente)
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
mp_token = os.environ.get('MP_ACCESS_TOKEN')

mp = None
if mp_token:
    try: 
        mp = mercadopago.SDK(mp_token)
        print(f"Mercado Pago SDK iniciado...")
    except Exception as e: 
        print(f"Erro ao iniciar MercadoPago SDK: {e}")

def renovar_assinatura(user_id=None, email=None, method='manual', valor_pago=0.0, plan_type=None):
    u = None
    if user_id: u = User.query.get(int(user_id))
    elif email: u = User.query.filter_by(email=email).first()
    
    if u:
        hoje = datetime.now().date()
        base = hoje
        if u.validade:
            val_atual = u.validade
            if isinstance(val_atual, str):
                try: val_atual = datetime.strptime(val_atual, '%Y-%m-%d').date()
                except: val_atual = hoje
            elif isinstance(val_atual, datetime): val_atual = val_atual.date()
            if val_atual > hoje: base = val_atual
            
        u.validade = (base + timedelta(days=30))
        u.category = 'subscriber'
        u.payment_method = method
        
        if plan_type:
            u.plan_type = plan_type
        else:
            val_float = float(valor_pago)
            if val_float < 15.00 and val_float > 8.00:
                if u.referral_balance > 0: u.plan_type = 'premium'
                else: u.plan_type = 'basic'
            elif val_float >= 19.00: u.plan_type = 'premium'
            else: u.plan_type = 'premium'
        
        val_float = float(valor_pago)
        if val_float > 0 and val_float < 15.00:
            if u.referral_balance > 0: u.referral_balance -= 1
                
        if u.referred_by and not u.referral_bonus_given:
            try:
                referrer = User.query.get(u.referred_by)
                if referrer:
                    referrer.referral_balance += 1
                    msg = f"🎉 Parabéns! Sua indicação ({u.nome.split()[0]}) assinou. Você ganhou 50% de desconto na próxima renovação!"
                    db.session.add(Notification(user_id=referrer.id, message=msg))
                    u.referral_bonus_given = True
            except: pass
        
        try: db.session.commit()
        except: db.session.rollback()

@bp.route('/assinar', endpoint='assinar')
@login_required
def assinar():
    tem_desconto = current_user.referral_balance > 0
    chaves_ok = bool(os.environ.get('STRIPE_PUBLIC_KEY'))
    is_dev = current_app.debug or os.environ.get('CODESPACES') == 'true'
    show_mock = is_dev or not chaves_ok
    msg = request.args.get('msg')
    
    return render_template('pagamento_pro.html', 
                           stripe_public_key=os.environ.get('STRIPE_PUBLIC_KEY'), 
                           email=current_user.email,
                           tem_desconto=tem_desconto,
                           show_mock=show_mock,
                           msg=msg)

@bp.route('/gerenciar_assinatura', endpoint='gerenciar')
@login_required
def gerenciar_assinatura():
    if not stripe.api_key: return redirect(url_for('main.assinatura') + "?msg=erro_config")
    try:
        customers = stripe.Customer.list(email=current_user.email, limit=1)
        if customers.data:
            session = stripe.billing_portal.Session.create(
                customer=customers.data[0].id,
                return_url=url_for('main.assinatura', _external=True)
            )
            return redirect(session.url)
        else: return redirect(url_for('main.assinatura') + "?msg=sem_cartao")
    except Exception as e: return redirect(url_for('main.assinatura') + "?msg=erro_stripe")

@bp.route('/mock_success', methods=['POST'])
@login_required
def mock_success():
    is_dev = current_app.debug or os.environ.get('CODESPACES') == 'true'
    if not is_dev and os.environ.get('STRIPE_SECRET_KEY') and 'live' in os.environ.get('STRIPE_SECRET_KEY'): 
        return "Acesso negado em produção", 403
    renovar_assinatura(user_id=current_user.id, method='mock_test', valor_pago=19.90, plan_type='premium')
    return redirect(url_for('payments.sucesso'))

@bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    if not stripe.api_key: return jsonify({'error': 'Stripe não configurado'}), 500
    try:
        data = request.get_json() or {}
        plan_key = data.get('plan', 'premium') 
        plano = current_app.config['PLANS'].get(plan_key, current_app.config['PLANS']['premium'])
        
        discounts = []
        if current_user.referral_balance > 0 and plan_key == 'premium':
            coupon_id = plano.get('stripe_coupon_id')
            if coupon_id: discounts = [{'coupon': coupon_id}]

        session = stripe.checkout.Session.create(
            customer_email=current_user.email,
            payment_method_types=['card'],
            line_items=[{'price': plano['stripe_price_id'], 'quantity': 1}],
            discounts=discounts,
            mode='subscription',
            success_url=url_for('payments.sucesso', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('payments.assinar', _external=True),
            client_reference_id=str(current_user.id),
            metadata={'plan_type': plan_key}
        )
        return jsonify({'id': session.id})
    except Exception as e: return jsonify({'error': str(e)}), 403

@bp.route('/create-pix-payment', methods=['POST'])
@login_required
def create_pix_payment():
    if not mp_token:
        print("ERRO: MP_ACCESS_TOKEN ausente.")
        return jsonify({'error': 'Configuração PIX ausente no servidor.'}), 503
        
    if not mp: 
        return jsonify({'error': 'SDK do Mercado Pago não inicializou.'}), 503
        
    try:
        data = request.get_json() or {}
        plan_key = data.get('plan', 'premium')
        plano = current_app.config['PLANS'].get(plan_key, current_app.config['PLANS']['premium'])
        valor_float = float(plano['valor'])
        
        if current_user.referral_balance > 0 and plan_key == 'premium':
            valor_float = valor_float / 2.0
            description = f"MotoristaPro - {plano['nome']} (50% OFF)"
        else:
            description = f"MotoristaPro - {plano['nome']}"

        # Tratamento de email para Sandbox
        payer_email = current_user.email
        if '@' not in payer_email or 'teste' in payer_email:
            payer_email = "test_user_123@test.com"

        # CORREÇÃO DO ERRO DE URL (ITEM CRÍTICO)
        # Se for localhost ou IP local, NÃO envia o notification_url
        notif_url = url_for('payments.mp_webhook', _external=True).replace('http://', 'https://')
        
        # Filtros de URL inválida para Webhook
        if 'localhost' in notif_url or '127.0.0.1' in notif_url or '.local' in notif_url:
            notif_url = None

        payment_data = {
            "transaction_amount": valor_float,
            "description": description,
            "payment_method_id": "pix",
            "payer": {
                "email": payer_email,
                "first_name": current_user.nome.split()[0] if current_user.nome else "User",
                "last_name": "App"
            },
            "external_reference": str(current_user.id),
            "metadata": {"plan_type": plan_key}
        }
        
        # Só adiciona a chave se a URL for válida
        if notif_url:
            payment_data["notification_url"] = notif_url

        pref = mp.payment().create(payment_data)
        
        if pref["status"] == 201:
            r = pref["response"]
            return jsonify({
                'qr_code': r['point_of_interaction']['transaction_data']['qr_code'], 
                'qr_code_base64': r['point_of_interaction']['transaction_data']['qr_code_base64'], 
                'valor': valor_float
            })
        else:
            error_msg = pref.get("response", {}).get("message", "Erro desconhecido")
            print(f"ERRO MP PIX: {error_msg} - Dados: {payment_data}")
            return jsonify({'error': f"Mercado Pago recusou: {error_msg}"}), 500
            
    except Exception as e: 
        print(f"EXCEÇÃO PIX: {str(e)}")
        return jsonify({'error': f"Erro interno: {str(e)}"}), 500

@bp.route('/webhook/stripe', methods=['POST'])
@csrf.exempt
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    try: event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except: return 'Error', 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        amount_paid = Decimal(session.get('amount_total', 0)) / 100
        plan_type = session.get('metadata', {}).get('plan_type', 'premium')
        renovar_assinatura(user_id=session.get('client_reference_id'), email=session.get('customer_email'), method='card', valor_pago=amount_paid, plan_type=plan_type)

    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        if invoice.get('billing_reason') == 'subscription_create': return jsonify({'status': 'ignored'})
        amount_paid = Decimal(invoice.get('amount_paid', 0)) / 100
        renovar_assinatura(email=invoice.get('customer_email'), method='card', valor_pago=amount_paid)
            
    return jsonify({'status': 'success'})

@bp.route('/webhook/mercadopago', methods=['POST'])
@csrf.exempt
def mp_webhook():
    if not mp: return jsonify({'status': 'ignored'})
    if request.args.get('type') == 'payment':
        try:
            pay = mp.payment().get(request.args.get('data.id'))['response']
            if pay['status'] == 'approved': 
                amount_paid = Decimal(str(pay.get('transaction_amount', 0)))
                plan_type = pay.get('metadata', {}).get('plan_type')
                renovar_assinatura(user_id=pay['external_reference'], method='pix', valor_pago=amount_paid, plan_type=plan_type)
        except: pass
    return jsonify({'status': 'ok'})

@bp.route('/sucesso', endpoint='sucesso')
def sucesso(): return render_template('pagamento_sucesso.html')



