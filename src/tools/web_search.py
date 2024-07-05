import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict
import html
from config.caching.caching import persistent_cache_decorator, memory_cache_decorator

@persistent_cache_decorator
@memory_cache_decorator
async def perform_web_search(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    url = f"https://html.duckduckgo.com/html/?q={query}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                content = await response.text()
            
            soup = BeautifulSoup(content, 'html.parser')
            
            results = []
            for result in soup.find_all('div', class_='result__body')[:num_results]:
                title = result.find('a', class_='result__a')
                snippet = result.find('a', class_='result__snippet')
                link = title.get('href') if title else ''
                
                results.append({
                    "title": html.unescape(title.text if title else ""),
                    "link": link,
                    "snippet": html.unescape(snippet.text if snippet else ""),
                    "displayLink": link
                })
            
            return results
        
        except aiohttp.ClientError as e:
            print(f"An error occurred while performing the web search: {e}")
            return []

def summarize_search_results(results: List[Dict[str, str]], max_chars: int = 1000) -> str:
    summary = "Web search results:\n\n"
    char_count = len(summary)
    
    for item in results:
        result_text = f"- {item['title']}\n  {item['link']}\n  {item['snippet']}\n\n"
        if char_count + len(result_text) > max_chars:
            break
        summary += result_text
        char_count += len(result_text)
        
    return summary.strip()

async def web_search_tool(query: str, num_results: int = 5, max_chars: int = 1000) -> str:
    results = await perform_web_search(query, num_results)
    return summarize_search_results(results, max_chars)
