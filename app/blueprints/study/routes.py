from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, session
from flask_login import login_required, current_user
from datetime import datetime, timezone
from app.models import db, Deck, StudySession, Flashcard, FlashcardResult

study_bp = Blueprint('study', __name__)

@study_bp.route('/<int:deck_id>')
@login_required
def mode_selection(deck_id):
    deck = Deck.query.get_or_404(deck_id)
    if deck.user_id != current_user.id:
        abort(403)
        
    flashcard_count = Flashcard.query.filter_by(deck_id=deck.id).count()
    if flashcard_count == 0:
        flash('Este mazo no tiene flashcards. Añade algunas para poder estudiar.', 'warning')
        return redirect(url_for('decks.view_deck', id=deck.id))
        
    return render_template('study/mode.html', deck=deck)

@study_bp.route('/<int:deck_id>/flashcards')
@login_required
def start_flashcards(deck_id):
    deck = Deck.query.get_or_404(deck_id)
    if deck.user_id != current_user.id:
        abort(403)
        
    flashcards = Flashcard.query.filter_by(deck_id=deck.id).order_by(Flashcard.order_index).all()
    if not flashcards:
        flash('El mazo está vacío.', 'warning')
        return redirect(url_for('decks.view_deck', id=deck.id))
        
    study_session = StudySession(
        user_id=current_user.id,
        deck_id=deck.id,
        mode='flashcard',
        total_cards=len(flashcards)
    )
    db.session.add(study_session)
    db.session.commit()
    
    session[f'study_queue_{study_session.id}'] = [f.id for f in flashcards]
    session[f'study_current_idx_{study_session.id}'] = 0
    session[f'study_incorrect_{study_session.id}'] = []
    
    return redirect(url_for('study.play_flashcard', session_id=study_session.id))

@study_bp.route('/session/<int:session_id>/play', methods=['GET', 'POST'])
@login_required
def play_flashcard(session_id):
    study_session = StudySession.query.get_or_404(session_id)
    if study_session.user_id != current_user.id or study_session.completed:
        abort(403)
        
    queue_key = f'study_queue_{study_session.id}'
    idx_key = f'study_current_idx_{study_session.id}'
    queue = session.get(queue_key, [])
    idx = session.get(idx_key, 0)
    
    if idx >= len(queue):
        return redirect(url_for('study.finish_session', session_id=study_session.id))
        
    flashcard_id = queue[idx]
    flashcard = Flashcard.query.get(flashcard_id)
    
    if request.method == 'POST':
        remembered_str = request.form.get('remembered')
        if remembered_str in ['true', 'false']:
            remembered = remembered_str == 'true'
            
            existing_result = FlashcardResult.query.filter_by(session_id=study_session.id, flashcard_id=flashcard.id).first()
            if not existing_result:
                result = FlashcardResult(
                    session_id=study_session.id,
                    flashcard_id=flashcard.id,
                    remembered=remembered
                )
                db.session.add(result)
                if remembered:
                    study_session.correct_count += 1
                else:
                    study_session.incorrect_count += 1
                db.session.commit()
                
            if not remembered:
                incorrect_key = f'study_incorrect_{study_session.id}'
                incorrect_list = session.get(incorrect_key, [])
                if flashcard.id not in incorrect_list:
                    queue.append(flashcard.id)
                    incorrect_list.append(flashcard.id)
                    session[incorrect_key] = incorrect_list
                    session[queue_key] = queue
            
            session[idx_key] = idx + 1
            return redirect(url_for('study.play_flashcard', session_id=study_session.id))
            
    progress_pct = int((idx / max(len(queue), 1)) * 100)
    return render_template('study/flashcard_player.html', session=study_session, flashcard=flashcard, progress=progress_pct, current=idx+1, total=len(queue))

@study_bp.route('/session/<int:session_id>/finish', methods=['GET', 'POST'])
@login_required
def finish_session(session_id):
    study_session = StudySession.query.get_or_404(session_id)
    if study_session.user_id != current_user.id:
        abort(403)
        
    if not study_session.completed:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        study_session.completed = True
        study_session.finished_at = now
        
        # Ensure started_at is also treated as naive UTC for calculation
        started = study_session.started_at
        if started.tzinfo is not None:
            started = started.replace(tzinfo=None)
            
        delta = now - started
        study_session.duration_seconds = int(delta.total_seconds())
        
        deck = study_session.deck
        deck.last_studied_at = now
        
        db.session.commit()
        
    return redirect(url_for('study.session_summary', session_id=study_session.id))

@study_bp.route('/session/<int:session_id>/summary')
@login_required
def session_summary(session_id):
    study_session = StudySession.query.get_or_404(session_id)
    if study_session.user_id != current_user.id:
        abort(403)
        
    pct = 0
    if study_session.total_cards > 0:
        pct = int((study_session.correct_count / study_session.total_cards) * 100)
        
    minutes = study_session.duration_seconds // 60
    seconds = study_session.duration_seconds % 60
    time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
        
    return render_template('study/summary.html', session=study_session, pct=pct, time_str=time_str)

@study_bp.route('/<int:deck_id>/exam')
@login_required
def start_exam(deck_id):
    # For now, exam is similar to flashcards but timed and no immediate feedback.
    # To keep implementation simple, we just redirect to flashcards.
    flash('Modo examen redirigido a flashcards por ahora.', 'info')
    return redirect(url_for('study.start_flashcards', deck_id=deck_id))
