import csv
from io import StringIO
import logging

logger = logging.getLogger(__name__)


def parse_quiz_file(content: str, file_type: str) -> list:
    questions = []
    
    try:
        if file_type == "csv":
            reader = csv.reader(StringIO(content))
            rows = list(reader)
        else:
            rows = [line.split("|") for line in content.strip().split("\n") if line.strip()]
        
        for idx, row in enumerate(rows, 1):
            if len(row) < 6:
                logger.warning(f"Skipping row {idx}: insufficient columns")
                continue
            
            row = [cell.strip() for cell in row]
            
            try:
                correct_option = int(row[5])
            except ValueError:
                logger.warning(f"Skipping row {idx}: invalid correct option")
                continue
            
            if correct_option < 0 or correct_option > 3:
                logger.warning(f"Skipping row {idx}: correct option out of range")
                continue
            
            question_data = {
                "question": row[0],
                "option_a": row[1],
                "option_b": row[2],
                "option_c": row[3],
                "option_d": row[4],
                "correct_option": correct_option,
                "explanation": row[6] if len(row) > 6 else ""
            }
            
            questions.append(question_data)
        
    except Exception as e:
        logger.error(f"Error parsing file: {e}")
        raise
    
    return questions


def validate_quiz_data(questions: list) -> tuple:
    if not questions:
        return False, "No questions provided"
    
    if len(questions) > 100:
        return False, "Maximum 100 questions allowed"
    
    for idx, q in enumerate(questions, 1):
        if not q.get("question") or len(q["question"]) < 5:
            return False, f"Question {idx}: Question text too short"
        
        if len(q["question"]) > 300:
            return False, f"Question {idx}: Question text too long (max 300 chars)"
        
        for opt in ["option_a", "option_b", "option_c", "option_d"]:
            if not q.get(opt) or len(q[opt]) < 1:
                return False, f"Question {idx}: Invalid option {opt}"
            
            if len(q[opt]) > 100:
                return False, f"Question {idx}: Option {opt} too long (max 100 chars)"
        
        if q.get("correct_option") not in [0, 1, 2, 3]:
            return False, f"Question {idx}: Invalid correct option"
        
        if q.get("explanation") and len(q["explanation"]) > 200:
            return False, f"Question {idx}: Explanation too long (max 200 chars)"
    
    return True, ""
```

===== requirements.txt =====
```
pyrogram==2.0.106
TgCrypto==1.2.5
motor==3.3.2
pandas==2.1.4
python-dotenv==1.0.0
