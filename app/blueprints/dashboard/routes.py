from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user
from datetime import datetime, timezone, timedelta
from app.models import Subject

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
        
    subjects = Subject.query.filter_by(user_id=current_user.id).order_by(Subject.created_at.desc()).all()
    
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    seven_days_ago = now - timedelta(days=7)
    
    subject_stats = []
    for subject in subjects:
        needs_review = any(
            (deck.last_studied_at is None or deck.last_studied_at < seven_days_ago) 
            for deck in subject.decks
        )
        
        # Calculate mastery (simplified mock or actual avg)
        # We can implement real mastery in progress module
        
        subject_stats.append({
            'subject': subject,
            'deck_count': len(subject.decks),
            'needs_review': needs_review
        })
        
    return render_template('dashboard/index.html', stats=subject_stats)
