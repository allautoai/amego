# StudyAmego

An AI-powered study platform for students.

## Installation

1. Clone repo
2. Create virtual environment: `python -m venv venv`
3. Activate virtual environment:
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Create a `.env` file in the root directory and set your API key:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   SECRET_KEY=your_random_secret_key_here
   ```
6. Initialize the database: `python create_db.py`
7. Run the application: `flask run` (or `python run.py`)
