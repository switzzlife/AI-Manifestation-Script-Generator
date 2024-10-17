import os
import stripe
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlparse
from werkzeug.utils import secure_filename
from __init__ import db, login_manager
from models import User, Script, Post, Comment, Subscription
from forms import LoginForm, RegistrationForm, ScriptGenerationForm, PostForm, CommentForm
from chat_request import send_openai_request

bp = Blueprint('main', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@bp.route('/')
@bp.route('/index')
def index():
    return render_template('index.html')

@bp.route('/generate_script', methods=['GET', 'POST'])
@login_required
def generate_script():
    if current_user.is_paid or current_user.free_scripts_count < 2:
        form = ScriptGenerationForm()
        if form.validate_on_submit():
            prompt = f"""Generate a manifestation script for the following:
            Goal: {form.goal.data}
            Focus Area: {form.focus.data}
            Duration: {form.duration.data} minutes
            Tone: {form.tone.data}
            Visualization Type: {form.visualization.data}
            Affirmation Style: {form.affirmation_style.data}
            
            The script should be engaging, motivational, and tailored to the user's specific goal and preferences."""

            try:
                script_content = send_openai_request(prompt)
                new_script = Script(content=script_content, user_id=current_user.id)
                db.session.add(new_script)
                if not current_user.is_paid:
                    current_user.free_scripts_count += 1
                db.session.commit()
                return redirect(url_for('main.view_script', script_id=new_script.id))
            except Exception as e:
                flash(f'Error generating script: {str(e)}')
                return redirect(url_for('main.generate_script'))

        return render_template('generate_script.html', title='Generate Script', form=form)
    else:
        flash('You have used all your free scripts. Please subscribe to generate more.')
        return redirect(url_for('main.subscribe'))

@bp.route('/subscribe/success')
@login_required
def subscribe_success():
    session_id = request.args.get('session_id')
    if not session_id:
        flash('Invalid session ID')
        return redirect(url_for('main.subscribe'))

    try:
        stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid':
            current_user.is_paid = True
            current_user.free_scripts_count = 0  # Reset free scripts count for paid users
            subscription = Subscription(
                user_id=current_user.id,
                stripe_customer_id=session.customer,
                stripe_subscription_id=session.subscription,
                active=True
            )
            db.session.add(subscription)
            db.session.commit()
            flash('Thank you for subscribing!')
        else:
            flash('Payment was not successful. Please try again.')
    except Exception as e:
        current_app.logger.error(f"Error processing subscription: {str(e)}")
        flash('An error occurred while processing your subscription. Please contact support.')

    return redirect(url_for('main.profile'))

@bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
    
    if not current_app.config.get('STRIPE_PRICE_ID'):
        current_app.logger.error("STRIPE_PRICE_ID is not set in the configuration")
        return jsonify(error="Server configuration error"), 500

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price': current_app.config['STRIPE_PRICE_ID'],
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=url_for('main.subscribe_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('main.subscribe', _external=True),
            client_reference_id=str(current_user.id),
        )
        return jsonify({'sessionId': checkout_session.id})
    except Exception as e:
        current_app.logger.error(f"Error creating checkout session: {str(e)}")
        return jsonify(error=str(e)), 500

@bp.route('/subscribe')
@login_required
def subscribe():
    return render_template('subscribe.html', stripe_publishable_key=current_app.config['STRIPE_PUBLIC_KEY'])

# Add other routes here...
