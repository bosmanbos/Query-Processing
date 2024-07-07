# AI Query Processing Project

This project is an advanced AI-powered query processing system that decomposes complex questions, analyzes them, and provides comprehensive answers using various AI models.

## Features

- Question decomposition into sub-questions
- Dynamic model selection based on question complexity
- Web search integration for enhanced context
- Multiple AI model integration (OpenAI GPT and Anthropic Claude)
- Caching system for improved performance
- Final answer synthesis and selection

## Setup

1. Clone the repository:
   ```
   git clone https://github.com/bosmanbos/ai-query-processing.git
   cd ai-query-processing
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up the .env file:
   Create a file named `.env` in the root directory of the project and add the following content:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```
   Replace `your_openai_api_key_here` and `your_anthropic_api_key_here` with your actual API keys.

4. Run the main script:
   ```
   python main.py
   ```

## Usage

When you run the main script, you will be prompted to enter a query. The system will then process your query, decompose it into sub-questions, analyze each sub-question, and provide a comprehensive answer.

## Project Structure

- `main.py`: The entry point of the application
- `config/`: Contains configuration files and core components
  - `agent.py`: Defines the Agent class for query processing
  - `Analyzer.py`: Implements question analysis functionality
  - `prompts.py`: Contains prompts used for various AI interactions
  - `question_decomp.py`: Handles question decomposition
- `tools/`: Contains utility functions
  - `web_search.py`: Implements web search functionality
- `caching/`: Implements caching mechanisms

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.
