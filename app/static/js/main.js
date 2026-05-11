document.addEventListener('DOMContentLoaded', () => {
    // Flashcard Flip Logic
    const flashcard = document.querySelector('.flashcard');
    const studyControls = document.querySelector('.study-controls');
    
    if (flashcard) {
        flashcard.addEventListener('click', () => {
            if (!flashcard.classList.contains('is-flipped')) {
                flashcard.classList.add('is-flipped');
                if (studyControls) {
                    studyControls.classList.add('show');
                }
            }
        });
    }

    // Auto-dismiss alerts
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});
