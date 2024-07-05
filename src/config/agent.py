import requests 
import json
from colorama import Fore, Style
from .prompts import query_context_prompt, final_check_prompt, decision_prompt
from .Analyzer import QuestionType, Expertise, QuestionAnalyzerAgent
from tools.web_search import web_search_tool
from .caching.caching import persistent_cache_decorator, memory_cache_decorator
from typing import List, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential
import aiohttp
import asyncio

class Agent:
    def __init__(self, openai_endpoint: str, anthropic_endpoint: str, openai_api_key: str, anthropic_api_key: str):
        self.openai_endpoint = openai_endpoint
        self.anthropic_endpoint = anthropic_endpoint
        self.openai_api_key = openai_api_key
        self.anthropic_api_key = anthropic_api_key
        self.question_analyzer = QuestionAnalyzerAgent(openai_api_key)
        print(f"{Fore.CYAN}Agent initialized with OpenAI and Anthropic endpoints.{Style.RESET_ALL}")

    def print_colored(self, message, color=Fore.WHITE, style=Style.NORMAL):
        print(f"{style}{color}{message}{Style.RESET_ALL}")


    async def analyze_and_select_model(self, sub_questions: List[Tuple[str, int, bool]]):
        analyzed_questions = await self.question_analyzer.analyze_questions(sub_questions)
        
        for question, difficulty, question_type, expertise, is_coding_related in analyzed_questions:
            model = self.select_model(difficulty, question_type, expertise, is_coding_related)
            self.print_colored(f"Question: {question}", Fore.CYAN)
            self.print_colored(f"Selected model: {model} for difficulty: {difficulty}, "
                               f"question type: {question_type.name}, "
                               f"required expertise: {expertise.name}, "
                               f"coding-related: {is_coding_related}", Fore.YELLOW)    
        
        return analyzed_questions


    def select_model(self, difficulty: int, question_type: QuestionType, expertise: Expertise, is_coding_related: bool) -> str:
        if is_coding_related:
            return "claude-3-5-sonnet-20240620"
        elif difficulty < 15 and question_type == QuestionType.FACTUAL and expertise == Expertise.GENERAL:
            return "claude-3-haiku-20240307"
        elif difficulty < 30 and question_type in [QuestionType.FACTUAL, QuestionType.ANALYTICAL] and expertise != Expertise.EXPERT:
            return "gpt-3.5-turbo"
        elif difficulty > 59:
            return "claude-3-5-sonnet-20240620"
        elif difficulty < 50 or (question_type == QuestionType.ANALYTICAL and expertise == Expertise.SPECIALIZED):
            return "gpt-4o"
        elif question_type == QuestionType.CREATIVE or expertise == Expertise.EXPERT:
            return "claude-3-5-sonnet-20240620"
        else:
            return "gpt-4o"  # Default to GPT-4o for any other case

    @persistent_cache_decorator
    @memory_cache_decorator
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def query_model_with_context(self, full_query: str, sub_question: str, difficulty: int, question_type: QuestionType, expertise: Expertise, is_coding_related: bool, needs_web_search: bool):
        model = self.select_model(difficulty, question_type, expertise, is_coding_related)
        self.print_colored(f"Selected model: {model} for difficulty: {difficulty}, "
                           f"question type: {question_type.name}, "
                           f"required expertise: {expertise.name}, "
                           f"coding-related: {is_coding_related}", Fore.YELLOW)

        context = f"Full Query Context: {full_query}\n\nSpecific Question to Answer: {sub_question}"
        if needs_web_search:
            self.print_colored("Performing web search for additional context...", Fore.CYAN)
            try:
                search_results = await web_search_tool(sub_question)
                context += f"\n\nWeb Search Results:\n{search_results}"
            except Exception as e:
                self.print_colored(f"Web search failed: {str(e)}", Fore.RED)
                context += "\n\nWeb Search Results: Unable to perform web search due to an error."

        messages = [
            {"role": "system", "content": query_context_prompt},
            {"role": "user", "content": context}
        ]
        
        try:
            if model.startswith("claude"):
                self.print_colored(f"Querying Anthropic API with model: {model}", Fore.MAGENTA)
                content = await self.query_anthropic(model, messages)
            else:  # OpenAI model
                self.print_colored(f"Querying OpenAI API with model: {model}", Fore.MAGENTA)
                content = await self.query_openai(model, messages)
            return content, model
        except Exception as e:
            self.print_colored(f"An error occurred while querying {model}: {str(e)}", Fore.RED)
            return f"Error: Failed to query {model}", model
        
    

    async def query_openai(self, model: str, messages: list):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.openai_api_key}',
        }
        payload = {
            'model': model,
            'messages': messages
        }
        self.print_colored("Sending request to OpenAI API...", Fore.CYAN)
        async with aiohttp.ClientSession() as session:
            async with session.post(self.openai_endpoint, headers=headers, json=payload) as response:
                response_json = await response.json()
                self.print_colored("Received response from OpenAI API", Fore.GREEN)
                return response_json['choices'][0]['message']['content']



    async def query_anthropic(self, model: str, messages: list):
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': self.anthropic_api_key,
            'anthropic-version': '2023-06-01'
        }
        system_message = next((msg['content'] for msg in messages if msg['role'] == 'system'), '')
        user_message = next((msg['content'] for msg in messages if msg['role'] == 'user'), '')

        payload = {
            'model': model,
            'max_tokens': 2048,
            'system': system_message,
            'messages': [
                {"role": "user", "content": user_message}
            ]
        }
        
        messages_endpoint = f"{self.anthropic_endpoint}/v1/messages"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(messages_endpoint, headers=headers, json=payload) as response:
                response_json = await response.json()
                self.print_colored("Received response from Anthropic API", Fore.GREEN)
                self.print_colored("Anthropic API Response:", Fore.YELLOW)
                print(json.dumps(response_json, indent=2))
                
                if 'error' in response_json:
                    raise Exception(response_json['error']['message'])
        
                content = " ".join([item['text'] for item in response_json['content']])
                return content



    async def multiple_final_checks(self, full_query: str, sub_responses: list) -> str:
        models = ["gpt-4o", "claude-3-5-sonnet-20240620", "gpt-3.5-turbo"]
        final_check_tasks = [self.final_check(full_query, sub_responses, model) for model in models]
        return await asyncio.gather(*final_check_tasks)
    

    async def final_check(self, full_query: str, sub_responses: list, model: str) -> str:
        consolidated_responses = "\n".join(sub_responses)
        
        messages = [
            {"role": "system", "content": final_check_prompt},
            {"role": "user", "content": f"Original Query: {full_query}\n\nResponses to sub-questions:\n{consolidated_responses}\n\nPlease provide a final, comprehensive answer to the original query based on these responses."}
        ]
        
        try:
            self.print_colored(f"Performing final check with {model}...", Fore.CYAN)
            if model.startswith("claude"):
                content = await self.query_anthropic(model, messages)
            else:
                content = await self.query_openai(model, messages)
            self.print_colored("Final check completed successfully", Fore.GREEN)
            return content
        except Exception as e:
            self.print_colored(f"An error occurred during final check with {model}: {str(e)}", Fore.RED)
            return f"Error: Failed to perform final check with {model}"
        
    
    async def decide_best_response(self, full_query: str, final_responses: List[str]) -> str:
        model = "claude-3-5-sonnet-20240620"
        consolidated_responses = "\n\n".join([f"Response {i+1}:\n{response}" for i, response in enumerate(final_responses)])
        
        messages = [
            {"role": "system", "content": decision_prompt},
            {"role": "user", "content": f"Original Query: {full_query}\n\nFinal Responses:\n{consolidated_responses}\n\nPlease analyze these responses and select the best one, or synthesize a new response if necessary."}
        ]
        
        try:
            self.print_colored("Making final decision on best response...", Fore.CYAN)
            content = await self.query_anthropic(model, messages)
            self.print_colored("Final decision completed successfully", Fore.GREEN)
            
            #Cheking to see if the chosen response gets shortened when it shouldnt be
            if len(content) < 0.8 * max(len(r) for r in final_responses):
                self.print_colored("Warning: Chosen response seems abbreviated. Verifying content...", Fore.YELLOW)
                verification_message = [
                    {"role": "system", "content": "You are a verification assistant. Your task is to ensure that the chosen response includes all necessary information, especially code snippets, from the original response. If any crucial information or code is missing, you must reincorporate it. MAKE SURE CODE FROM THE CHOSEN RESPONSE IS FULLY INCLUDED IN THE FINAL OUTPUT!!!!!!"},
                    {"role": "user", "content": f"Original responses:\n{consolidated_responses}\n\nChosen response:\n{content}\n\nPlease verify that the chosen response includes all necessary information, especially any code snippets, from the original responses. If anything crucial is missing, particularly code, please provide a corrected version that includes all necessary information and code."}
                ]
                content = await self.query_anthropic(model, verification_message)
                self.print_colored("Content verification completed", Fore.GREEN)
            return content
        except Exception as e:
            self.print_colored(f"An error occured during final decision: {str(e)}", Fore.RED)
            return f"Error: Failed to make final decision"
