from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError
from datetime import datetime, timezone, timedelta
from app.models import db, Subject

subjects_bp = Blueprint('subjects', __name__)

class SubjectForm(FlaskForm):
    name = StringField('Nombre', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Descripción')
    color = StringField('Color HEX', default='#4F46E5', validators=[Length(max=20)])
    submit = SubmitField('Guardar')

    def __init__(self, original_name=None, *args, **kwargs):
        super(SubjectForm, self).__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, name):
        if self.original_name and name.data.lower() == self.original_name.lower():
            return
        subject = Subject.query.filter(Subject.user_id == current_user.id, Subject.name.ilike(name.data)).first()
        if subject:
            raise ValidationError('Ya tienes una asignatura con este nombre.')

@subjects_bp.route('/')
@login_required
def list_subjects():
    subjects = Subject.query.filter_by(user_id=current_user.id).order_by(Subject.created_at.desc()).all()
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    
    for subject in subjects:
        subject.needs_review = any(
            (deck.last_studied_at is None or deck.last_studied_at < seven_days_ago) 
            for deck in subject.decks
        )
        
    return render_template('subjects/list.html', subjects=subjects)

@subjects_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_subject():
    count = Subject.query.filter_by(user_id=current_user.id).count()
    if count >= 20:
        flash('Has alcanzado el límite máximo de 20 asignaturas.', 'warning')
        return redirect(url_for('subjects.list_subjects'))
        
    form = SubjectForm()
    if form.validate_on_submit():
        subject = Subject(
            user_id=current_user.id,
            name=form.name.data,
            description=form.description.data,
            color=form.color.data
        )
        db.session.add(subject)
        try:
            db.session.commit()
            flash('Asignatura creada exitosamente.', 'success')
            return redirect(url_for('subjects.list_subjects'))
        except Exception:
            db.session.rollback()
            flash('Error al crear la asignatura.', 'danger')
            
    return render_template('subjects/form.html', form=form, title="Nueva Asignatura")

@subjects_bp.route('/<int:id>')
@login_required
def view_subject(id):
    subject = Subject.query.get_or_404(id)
    if subject.user_id != current_user.id:
        abort(403)
    return render_template('subjects/view.html', subject=subject)

@subjects_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_subject(id):
    subject = Subject.query.get_or_404(id)
    if subject.user_id != current_user.id:
        abort(403)
        
    form = SubjectForm(original_name=subject.name, obj=subject)
    if form.validate_on_submit():
        subject.name = form.name.data
        subject.description = form.description.data
        subject.color = form.color.data
        try:
            db.session.commit()
            flash('Asignatura actualizada.', 'success')
            return redirect(url_for('subjects.view_subject', id=subject.id))
        except Exception:
            db.session.rollback()
            flash('Error al actualizar.', 'danger')
            
    return render_template('subjects/form.html', form=form, title="Editar Asignatura")

@subjects_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_subject(id):
    subject = Subject.query.get_or_404(id)
    if subject.user_id != current_user.id:
        abort(403)
        
    db.session.delete(subject)
    try:
        db.session.commit()
        flash('Asignatura eliminada.', 'success')
    except Exception:
        db.session.rollback()
        flash('Error al eliminar.', 'danger')
        
    return redirect(url_for('subjects.list_subjects'))
