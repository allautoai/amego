from flask import Blueprint, render_template, abort, request
from flask_login import login_required, current_user
from datetime import datetime, timezone, timedelta
from app.models import db, StudySession, Subject, Deck

progress_bp = Blueprint('progress', __name__)

@progress_bp.route('/')
@login_required
def index():
    sessions = StudySession.query.filter_by(user_id=current_user.id, completed=True).order_by(StudySession.finished_at.desc()).all()
    
    streak = 0
    current_date = datetime.now(timezone.utc).date()
    
    dates_studied = set()
    for s in sessions:
        if s.finished_at:
            dates_studied.add(s.finished_at.date())
            
    check_date = current_date
    if check_date not in dates_studied:
        check_date -= timedelta(days=1)
        
    while check_date in dates_studied:
        streak += 1
        check_date -= timedelta(days=1)
        
    subjects = Subject.query.filter_by(user_id=current_user.id).all()
    mastery_data = []
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    for subject in subjects:
        subject_sessions = StudySession.query.join(Deck).filter(
            Deck.subject_id == subject.id,
            StudySession.completed == True,
            StudySession.finished_at >= seven_days_ago
        ).all()
        
        total_correct = sum(s.correct_count for s in subject_sessions)
        total_cards = sum(s.total_cards for s in subject_sessions)
        
        mastery = 0
        if total_cards > 0:
            mastery = int((total_correct / total_cards) * 100)
            
        mastery_data.append({
            'subject': subject,
            'mastery': mastery,
            'sessions_count': len(subject_sessions)
        })
        
    return render_template('progress/index.html', streak=streak, mastery_data=mastery_data, recent_sessions=sessions[:5])

@progress_bp.route('/history')
@login_required
def history():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    pagination = StudySession.query.filter_by(user_id=current_user.id, completed=True)\
        .order_by(StudySession.finished_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
        
    return render_template('progress/history.html', pagination=pagination)

@progress_bp.route('/history/<int:session_id>')
@login_required
def session_detail(session_id):
    study_session = StudySession.query.get_or_404(session_id)
    if study_session.user_id != current_user.id:
        abort(403)
        
    results = study_session.flashcard_results
    
    return render_template('progress/detail.html', session=study_session, results=results)
