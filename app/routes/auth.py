from flask import Blueprint, render_template, request, redirect, url_for, jsonify, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta, date
from app.extensions import db, limiter, csrf
from app.models import User, Notification
from app.utils import init_user_configs
from app.services.gamification import AchievementService
from firebase_admin import auth as firebase_auth
import secrets
import string
import os

bp = Blueprint('auth', __name__)

def generate_referral_code():
    chars = string.ascii_uppercase + string.digits
    for _ in range(10): 
        code = ''.join(secrets.choice(chars) for _ in range(6))
        if not db.session.query(User.id).filter_by(referral_code=code).first():
            return code
    return secrets.token_hex(4).upper()

@bp.route('/login', methods=['GET'], endpoint='login')
def login_view():
    if current_user.is_authenticated: return redirect(url_for('dashboard.index'))
    return render_template('login.html')

@bp.route('/register', methods=['GET'], endpoint='register')
def register_view():
    if current_user.is_authenticated: return redirect(url_for('dashboard.index'))
    return render_template('register.html')

@bp.route('/auth/firebase_auth', methods=['POST'], endpoint='firebase_auth')
@csrf.exempt
@limiter.limit("20 per minute")
def firebase_auth_handler():
    try:
        data = request.get_json()
        id_token = data.get('idToken')
        nome = data.get('nome', 'Motorista')
        photo_url = data.get('photoURL') 
        whatsapp = data.get('whatsapp', '')
        referral_code_input = data.get('referralCode') 
        
        # 1. Validar Token Google
        try:
            decoded_token = firebase_auth.verify_id_token(id_token)
            email = decoded_token['email']
        except Exception as e:
            print(f"Erro Token Google: {e}")
            return jsonify({'success': False, 'message': 'Sessão inválida. Tente novamente.'}), 400
        
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # === CRIAÇÃO DE USUÁRIO (Blindada) ===
            try:
                hoje = date.today()
                # CORREÇÃO: Trial de 7 dias exatos (Antes estava 6)
                validade_trial = hoje + timedelta(days=7)
                
                referrer_id = None
                if referral_code_input:
                    clean_code = referral_code_input.upper().strip()
                    referrer = db.session.query(User.id).filter_by(referral_code=clean_code).first()
                    if referrer: referrer_id = referrer.id
                
                user = User(
                    email=email, 
                    nome=nome, 
                    whatsapp=whatsapp, 
                    password_hash="FIREBASE_SOCIAL",
                    validade=validade_trial, 
                    data_cadastro=hoje, 
                    last_seen_version='0.0', 
                    is_confirmed=True, 
                    category='trial', 
                    referral_code=generate_referral_code(), 
                    referred_by=referrer_id, 
                    referral_balance=0, 
                    referral_bonus_given=False,
                    plan_type='premium',
                    profile_image=photo_url 
                )
                user.set_password(secrets.token_hex(32))
                
                db.session.add(user)
                db.session.commit() # COMMIT 1
                
            except Exception as e:
                db.session.rollback()
                print(f"Erro Fatal ao Criar User: {e}")
                return jsonify({'success': False, 'message': 'Erro ao registar conta.'}), 500

            # === PÓS-CRIAÇÃO ===
            try:
                init_user_configs(user)
                
                primeiro_nome = nome.split()[0] if nome else "Motorista"
                welcome_msg = f"Olá, {primeiro_nome}! 🚗 Bem-vindo a bordo. Acesso via Google configurado com sucesso."
                db.session.add(Notification(user_id=user.id, message=welcome_msg, is_read=False))
                
                if referrer_id:
                    msg_ref = f"🎉 Seu amigo {primeiro_nome} cadastrou-se com o seu código! Se ele assinar o Premium, ganha 50% de desconto."
                    db.session.add(Notification(user_id=referrer_id, message=msg_ref, is_read=False))
                    
                db.session.commit() # COMMIT 2
            except Exception as e:
                print(f"Erro Pós-Criação (Ignorado): {e}")
            
        else:
            # === LOGIN ===
            try:
                if photo_url and not user.profile_image: user.profile_image = photo_url
                if not user.referral_code: user.referral_code = generate_referral_code()
                if whatsapp and user.whatsapp != whatsapp: user.whatsapp = whatsapp
                db.session.commit()
            except: pass
            
        # 3. LOGIN NA SESSÃO FLASK
        login_user(user, remember=True)
        
        # 4. GAMIFICAÇÃO
        try:
            AchievementService.get_badges_with_progress(user)
        except Exception as e:
            print(f"Erro Gamificação no Login (Ignorado): {e}")
        
        return jsonify({'success': True, 'redirect': url_for('dashboard.index')})
        
    except Exception as e:
        print(f"Auth Critical Error: {str(e)}") 
        return jsonify({'success': False, 'message': f'Erro interno: {str(e)}'}), 500

@bp.route('/auth/action', methods=['GET'], endpoint='action_handler')
def action_handler():
    return render_template('auth_action.html', mode=request.args.get('mode'), code=request.args.get('oobCode'))

@bp.route('/logout', endpoint='logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@bp.route('/recuperar_senha', endpoint='recuperar_senha')
def recuperar_senha(): return render_template('esqueci_senha.html')

@bp.route('/change_password_force', methods=['GET', 'POST'], endpoint='change_password_force')
@login_required
def change_password_force():
    if request.method == 'POST':
        nova = request.form.get('nova_senha')
        if nova and len(nova) >= 6:
            current_user.set_password(nova)
            current_user.is_temp_password = False
            db.session.commit()
            return redirect(url_for('dashboard.index'))
        else:
            return render_template('change_password.html', erro="A senha deve ter no mínimo 6 caracteres.")
    return render_template('change_password.html')

@bp.route('/admin/login', methods=['GET', 'POST'], endpoint='admin_login')
@limiter.limit("5 per minute")
def admin_login():
    erro = None
    admin_password = os.environ.get('ADMIN_PASSWORD')
    
    if not admin_password:
        if current_app.debug: 
            return "ERRO: Configure ADMIN_PASSWORD no .env ou Render.", 500
        else:
            return "Acesso administrativo desativado por segurança.", 403

    if request.method == 'POST':
        if request.form.get('senha') == admin_password: 
            session['is_admin'] = True
            return redirect(url_for('admin.dashboard'))
        else:
            erro = "Senha incorreta."
            
    return render_template('admin_login.html', erro=erro)



