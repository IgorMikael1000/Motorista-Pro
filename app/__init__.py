import os
import sys
import json
import logging
from flask import Flask, render_template, request, redirect, url_for
from app.config import Config
from app.extensions import db, login_manager, migrate, csrf, limiter
from app.models import User, Notification
from datetime import datetime
from sqlalchemy import inspect
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials

load_dotenv()

def create_app(config_class=None):
    app = Flask(__name__)
    
    if config_class is None:
        try:
            from app.config import Config
            config_class = Config
        except ImportError:
            class Config:
                SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_key')
                SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///local.db')
            config_class = Config

    app.config.from_object(config_class)
    
    # ATENÇÃO: Versão atualizada para limpar cache dos navegadores
    app.config['APP_VERSION'] = "v13.2-Onboarding"

    # --- CONFIGURAÇÃO DE CACHE BUSTING (AUTOMÁTICO) ---
    @app.url_defaults
    def hashed_url_for_static_file(endpoint, values):
        if 'static' == endpoint or endpoint.endswith('.static'):
            filename = values.get('filename')
            if filename:
                param_name = 'v'
                while param_name in values:
                    param_name = '_' + param_name
                values[param_name] = app.config['APP_VERSION']

    if not app.debug:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)

    try:
        if not firebase_admin._apps:
            creds_json = os.environ.get('FIREBASE_CREDENTIALS')
            if creds_json:
                cred_dict = json.loads(creds_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
    except Exception as e:
        app.logger.error(f"Firebase Error: {e}")

    firebase_config_frontend = os.environ.get('FIREBASE_CONFIG_FRONTEND', '{}')
    
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.utils import clean_phone_filter, float_to_time_filter
    app.jinja_env.filters['clean_phone'] = clean_phone_filter
    app.jinja_env.filters['float_to_time'] = float_to_time_filter

    from flask_login import current_user

    @app.context_processor
    def inject_global_vars():
        plan_info = app.config.get('PLANS', {}).get('mensal', {})
        unread = 0
        if current_user.is_authenticated:
            try:
                unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
            except: pass
        return dict(
            current_version=app.config['APP_VERSION'],
            unread_notifications=unread,
            plano_nome=plan_info.get('nome'),
            plano_valor=plan_info.get('valor_display'),
            FIREBASE_CONFIG_FRONTEND=firebase_config_frontend 
        )

    @app.before_request
    def check_maintenance_and_status():
        if request.endpoint and ('static' in request.endpoint or 'webhook' in request.endpoint or 'healthz' in request.endpoint):
            return

        if os.environ.get('MAINTENANCE_MODE') == 'True':
            if current_user.is_authenticated and current_user.email == 'admin@motoristapro.app': pass
            elif request.endpoint not in ['auth.login', 'auth.logout', 'auth.register', 'auth.firebase_auth', 'auth.action_handler']:
                return render_template('maintenance.html'), 503

        if current_user.is_authenticated:
            if current_user.validade:
                try:
                    hoje = datetime.now().date()
                    val = current_user.validade
                    if isinstance(val, str):
                        try: val = datetime.strptime(val, '%Y-%m-%d').date()
                        except: val = hoje
                    if val < hoje:
                        if current_user.category != 'expired':
                            current_user.category = 'expired'; db.session.commit()
                        whitelist = ['payments.', 'webhook', 'auth.', 'static', 'main.healthz']
                        if request.endpoint and not any(x in request.endpoint for x in whitelist):
                            stripe_key = os.environ.get('STRIPE_PUBLIC_KEY')
                            return render_template('bloqueio_assinatura.html', nome=current_user.nome, validade=val.strftime('%d/%m/%Y'), email=current_user.email, stripe_public_key=stripe_key)
                except Exception as e: app.logger.error(f"Erro check_status: {e}")

            if getattr(current_user, 'is_temp_password', False) and request.endpoint != 'auth.change_password_force':
                return redirect(url_for('auth.change_password_force'))

    print(">>> APP: Carregando Blueprints...")
    
    try:
        from app.routes.auth import bp as auth_bp
        from app.routes.main import bp as main_bp
        from app.routes.dashboard import bp as dashboard_bp
        from app.routes.admin import bp as admin_bp
        from app.routes.user_settings import bp as settings_bp
        from app.routes.payments import bp as payments_bp

        app.register_blueprint(auth_bp) 
        app.register_blueprint(main_bp) 
        app.register_blueprint(dashboard_bp)
        app.register_blueprint(admin_bp, url_prefix='/admin')
        app.register_blueprint(settings_bp)
        app.register_blueprint(payments_bp)
        
        print(">>> APP: Blueprints registrados com sucesso.")
    except Exception as e:
        print(f"XXX APP: Erro ao registrar Blueprints: {e}")
        raise e

    return app



