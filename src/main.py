import os
from typing import List, Tuple
from config.question_decomp import decompose_question
from tools.web_search import web_search_tool
from config.agent import Agent
from config.caching.caching import clear_persistent_cache, clear_memory_cache
from colorama import init, Fore, Style
import asyncio
from config.agent import Agent


from dotenv import load_dotenv
load_dotenv()

# Initialize colorama
init(autoreset=True)

api_key = os.getenv('OPENAI_API_KEY')
claude_key = os.getenv('ANTHROPIC_API_KEY')
os.environ['ANTHROPIC_API_KEY'] = claude_key
os.environ['OPENAI_API_KEY'] = api_key

def print_colored(message, color=Fore.WHITE, style=Style.NORMAL):
    print(f"{style}{color}{message}{Style.RESET_ALL}")


async def process_sub_question(agent: Agent, full_query: str, sub_question: Tuple[str, int, bool], analyzed_question: Tuple):
    sub_q, difficulty, needs_web_search = sub_question
    question_type, expertise, is_coding_related = analyzed_question[2:]
    
    context = f"Full Query Context: {full_query}\n\nSpecific Question to Answer: {sub_q}"
    
    if needs_web_search:
        print_colored(f"Performing web search for: {sub_q}", Fore.CYAN)
        try:
            search_results = await web_search_tool(sub_q)
            context += f"\n\nWeb Search Results:\n{search_results}"
        except Exception as e:
            print_colored(f"Web search failed: {str(e)}", Fore.RED)
            context += "\n\nWeb Search Results: Unable to perform web search due to an error."
    
    response, model_used = await agent.query_model_with_context(full_query, sub_q, difficulty, question_type, expertise, is_coding_related, needs_web_search)
    
    return (sub_q, difficulty, question_type, expertise, is_coding_related, model_used, response)

async def main(full_query):
    openai_endpoint = "https://api.openai.com/v1/chat/completions"
    anthropic_endpoint = "https://api.anthropic.com"
    decomp_model = 'gpt-4o' 
    
    print_colored("Starting question decomposition process...", Fore.CYAN, Style.BRIGHT)
    print_colored(f"Using model: {decomp_model}", Fore.YELLOW)
    
    # Step 1: Decompose the question with difficulty scores and web search decision (synchronous)
    sub_questions_with_info = decompose_question(api_key, decomp_model, full_query)
    
    print_colored("\nDecomposed sub-questions with difficulty and web search decision:", Fore.GREEN, Style.BRIGHT)
    for i, (sub_question, difficulty, needs_web_search) in enumerate(sub_questions_with_info, 1):
        print_colored(f"{i}. {sub_question} (Difficulty: {difficulty}, Needs Web Search: {needs_web_search})", Fore.GREEN)
    
    # Step 2: Create an agent and analyze each sub-question
    print_colored("\nCreating Agent...", Fore.CYAN, Style.BRIGHT)
    agent = Agent(openai_endpoint=openai_endpoint, anthropic_endpoint=anthropic_endpoint, 
                  openai_api_key=api_key, anthropic_api_key=claude_key)
    print_colored("Agent created successfully!", Fore.CYAN)
    analyzed_questions = await agent.analyze_and_select_model(sub_questions_with_info)
    
    # Step 3: Query models for sub-questions (asynchronous)
    print_colored("\nQuerying models for sub-questions...", Fore.MAGENTA, Style.BRIGHT)
    query_tasks = [
        process_sub_question(agent, full_query, sub_q_info, analyzed_q)
        for sub_q_info, analyzed_q in zip(sub_questions_with_info, analyzed_questions)
    ]
    responses = await asyncio.gather(*query_tasks)
    
    formatted_responses = []
    for i, (sub_q, difficulty, q_type, expertise, is_coding, model, response) in enumerate(responses, 1):
        formatted_responses.append(
            f"Sub-question {i}: {sub_q}\n"
            f"Difficulty: {difficulty}\n"
            f"Question Type: {q_type}\n"
            f"Expertise: {expertise}\n"
            f"Coding-related: {is_coding}\n"
            f"Model used: {model}\n"
            f"Answer: {response}\n"
        )
        
    # Step 4: Combine the responses
    print_colored("\nPerforming multiple final checks...", Fore.BLUE, Style.BRIGHT)
    final_responses = await agent.multiple_final_checks(full_query, formatted_responses)
    
    print_colored("\nFinal Responses from Different Models:", Fore.BLUE, Style.BRIGHT)
    for i, response in enumerate(final_responses, 1):
        print_colored(f"\nResponse {i}:", Fore.YELLOW)
        print(response)

    # Step 5: Decide on the best response
    print_colored("\nMaking final decision on the best response...", Fore.CYAN, Style.BRIGHT)
    final_answer = await agent.decide_best_response(full_query, final_responses)
    
    # CACHE CLEARING ------------
    # clear_memory_cache()
    # clear_persistent_cache()
    
    print_colored("\nFinal Consolidated Answer:", Fore.GREEN, Style.BRIGHT)
    return final_answer

if __name__ == "__main__":
    print('\n\n\n\n\n')
    full_query = input(">>>>>>>>> QUERY: ")
    
    result = asyncio.run(main(full_query))
    print(result)
