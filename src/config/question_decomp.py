import openai
from typing import List, Tuple
from .prompts import decomp_prompt


def decompose_question(api_key: str, model: str, query: str) -> List[Tuple[str, int]]:
    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": decomp_prompt},
            {"role": "user", "content": query}
        ],
        max_tokens=2048,
        temperature=0.2,
        n=1
    )
    sub_questions_with_difficulty = response.choices[0].message.content.strip().split("\n")
    result = []
    for item in sub_questions_with_difficulty:
        parts = item.split(" | ")
        if len(parts) == 3:
            question = parts[0].replace("Question: ", "").strip()
            difficulty = int(parts[1].replace("Difficulty: ", "").strip())
            needs_web_search = parts[2].replace("Needs Web Search: ", "").strip().lower() == "true"
            result.append((question, difficulty, needs_web_search))
    return result
