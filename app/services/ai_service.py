import os
import json
import google.generativeai as genai

def _get_gemini_model():
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("La clave de API de Gemini no está configurada")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-1.5-flash')

def generate_flashcards(text: str) -> list[dict]:
    model = _get_gemini_model()
    prompt = (
        "You are an expert study assistant. Generate exactly 5 flashcards from the following text.\n"
        "Return your response ONLY as a valid JSON array of objects. Do not include markdown blocks, "
        "backticks, or any other text.\n"
        "Each object must have exactly two string keys: 'question' and 'answer'.\n\n"
        f"Text:\n{text}"
    )
    
    try:
        response = model.generate_content(prompt, request_options={"timeout": 10.0})
        content = response.text.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        cards = json.loads(content)
        if not isinstance(cards, list):
            raise ValueError("La respuesta no es una lista JSON válida")
            
        valid_cards = []
        for card in cards[:5]:
            if 'question' in card and 'answer' in card:
                valid_cards.append({
                    'question': str(card['question']).strip(),
                    'answer': str(card['answer']).strip()
                })
        return valid_cards
    except Exception as e:
        raise Exception(f"Error al generar flashcards: {str(e)}")

def generate_quiz(text: str) -> list[dict]:
    model = _get_gemini_model()
    prompt = (
        "You are an expert study assistant. Generate exactly 3 multiple choice questions from the following text.\n"
        "Return your response ONLY as a valid JSON array of objects. Do not include markdown blocks, "
        "backticks, or any other text.\n"
        "Each object must have exactly three keys: \n"
        "- 'question': string\n"
        "- 'options': an array of exactly 4 strings\n"
        "- 'correct_index': an integer (0, 1, 2, or 3) representing the index of the correct option.\n\n"
        f"Text:\n{text}"
    )
    try:
        response = model.generate_content(prompt, request_options={"timeout": 10.0})
        content = response.text.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        questions = json.loads(content)
        if not isinstance(questions, list):
            raise ValueError("La respuesta no es una lista JSON válida")
            
        valid_questions = []
        for q in questions[:3]:
            if 'question' in q and 'options' in q and 'correct_index' in q:
                if isinstance(q['options'], list) and len(q['options']) == 4:
                    try:
                        correct_idx = int(q['correct_index'])
                        if 0 <= correct_idx <= 3:
                            valid_questions.append({
                                'question': str(q['question']).strip(),
                                'options': [str(opt).strip() for opt in q['options']],
                                'correct_index': correct_idx
                            })
                    except ValueError:
                        pass
        return valid_questions
    except Exception as e:
        raise Exception(f"Error al generar el quiz: {str(e)}")
