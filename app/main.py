from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import os
from dotenv import load_dotenv
import requests
import json
from groq import Groq
import openai

# Load environment variables
load_dotenv()

# API Keys
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
openai.api_key = os.getenv("OPENAI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API")
BRAVE_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY")
TELEGRAM_API = os.getenv("TELEGRAM_TOKEN")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text
    if "@askalvi" in message_text.lower():
        question = message_text.split("@askalvi")[1].strip()

        # Choose Search Engine (Brave or Serper)
        search_engine = "serper"  # Change to "brave" if needed

        # Step 1: Perform Web Search
        if search_engine == "serper":
            search_url = "https://google.serper.dev/search"
            headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
            search_data = {"q": question, "num": 5}
            search_response = requests.post(search_url, headers=headers, data=json.dumps(search_data))
            search_results = search_response.json()
            snippets = [result.get("snippet", "") for result in search_results.get("organic", [])[:3]]
            links = [result.get("link", "") for result in search_results.get("organic", [])[:3]]
        else:  # Use Brave Search
            search_url = "https://api.search.brave.com/res/v1/web/search"
            headers = {"Accept": "application/json", "X-Subscription-Token": BRAVE_API_KEY}
            params = {"q": question, "count": 5}
            search_response = requests.get(search_url, headers=headers, params=params)
            search_results = search_response.json()
            snippets = [result.get("description", "") for result in search_results.get("web", {}).get("results", [])[:3]]
            links = [result.get("url", "") for result in search_results.get("web", {}).get("results", [])[:3]]

        # Step 2: Generate Answer with Groq or OpenAI
        llm_provider = "groq"  # Change to "openai" if preferred

        system_prompt = f"""
        Answer the user's question concisely using these search results:
        {snippets}
        """
        if llm_provider == "groq":
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                model="mixtral-8x7b-32768"  # Or "llama3-70b-8192"
            )
            answer = chat_completion.choices[0].message.content
        else:  # Use OpenAI GPT-4
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ]
            )
            answer = response.choices[0].message['content']

        # Step 3: Send Answer with Sources
        response_text = f"{answer}\n\n🔍 Sources:\n" + "\n".join([f"- {link}" for link in links[:3]])
        await update.message.reply_text(response_text)

if __name__ == "__main__":
    app = Application.builder().token(TELEGRAM_API).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
