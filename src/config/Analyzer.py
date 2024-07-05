import asyncio
import aiohttp
from enum import Enum
from typing import List, Tuple
from .prompts import analyze_question_prompt

class QuestionType(Enum):
    FACTUAL = 1
    ANALYTICAL = 2
    CREATIVE = 3
    TECHNICAL = 4

class Expertise(Enum):
    GENERAL = 1
    SPECIALIZED = 2
    EXPERT = 3

class QuestionAnalyzerAgent:
    def __init__(self, openai_api_key: str):
        self.api_key = openai_api_key
        self.api_url = "https://api.openai.com/v1/chat/completions"

    async def analyze_question(self, question: str, difficulty: int) -> Tuple[QuestionType, Expertise, bool]:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": analyze_question_prompt},
                    {"role": "user", "content": f"Analyze the following question (difficulty: {difficulty}/100) and determine its type (FACTUAL, ANALYTICAL, CREATIVE, TECHNICAL) and required expertise level (GENERAL, SPECIALIZED, EXPERT).\n\nQuestion: {question}"}
                ],
                "temperature": 0.3
            }
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with session.post(self.api_url, json=payload, headers=headers) as response:
                result = await response.json()
                analysis = result['choices'][0]['message']['content']
                
                # Parse the response to extract QuestionType and Expertise
                question_type = QuestionType.ANALYTICAL  # Default
                expertise = Expertise.GENERAL  # Default
                is_coding_related = False
                
                if "FACTUAL" in analysis:
                    question_type = QuestionType.FACTUAL
                elif "CREATIVE" in analysis:
                    question_type = QuestionType.CREATIVE
                elif "TECHNICAL" in analysis:
                    question_type = QuestionType.TECHNICAL
                
                if "EXPERT" in analysis:
                    expertise = Expertise.EXPERT
                elif "SPECIALIZED" in analysis:
                    expertise = Expertise.SPECIALIZED
                
                if "CODING=TRUE" in analysis:
                    is_coding_related = True
                
                return question_type, expertise, is_coding_related
                

    async def analyze_questions(self, questions: List[Tuple[str, int, bool]]) -> List[Tuple[str, int, QuestionType, Expertise]]:
        tasks = [self.analyze_question(question, difficulty) for question, difficulty, _ in questions]
        results = await asyncio.gather(*tasks)
        
        return [(q[0], q[1], r[0], r[1], r[2]) for q, r in zip(questions, results)]
