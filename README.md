🤖 Artery AI Sales Agent - Smart WooCommerce Chatbot
An intelligent, context-aware sales agent designed for E-commerce stores. Built with Python, Flask, OpenAI, and WooCommerce API.

📖 Overview
This project is an advanced AI Sales Agent built for a WooCommerce art gallery. Unlike standard chatbots that rely on simple keywords, this agent is designed to understand intent, translate abstract user requests (e.g., "I want something calm for the living room") into precise product queries, and perform automatic Lead Capture.

The system bridges the gap between the physical and digital buying experience using a unique semantic search engine and session context management.

🚀 Key Features
🧠 1. Smart Semantic Search
The bot utilizes a custom "Concept Mapping" logic rather than simple keyword matching:

Emotion-to-Product Translation: The system understands that "Calm" maps to pastel colors, sea views, and nature, while "Luxury" maps to gold, black, and brand names.

Scoring Algorithm: An internal algorithm ranks results based on relevance, giving a "boost" to Best Seller items.

Fallback Logic: If a specific search yields no results, the bot gracefully degrades to broader categories or trending recommendations.

💬 2. Context & Memory Management
Anti-Looping: The bot tracks which products have already been shown in the current session to prevent repetition (Smart Pagination).

Context Reset: Intelligent detection of topic changes. If a user switches from "Animals" to "Abstract", the bot resets the context to ensure clean search results.

🎣 3. Lead Generation & CRM
Automatic Detection: Uses Regex to identify phone numbers within natural language conversations.

Smart Storage: Filters duplicates and saves leads to a JSON file (scalable to DB/CRM) with the conversation context.

Human Handoff: The bot knows when to ask for contact details and when to provide a direct WhatsApp link for complex inquiries.

🎨 4. Dynamic UI Generation
The backend generates dynamic HTML responses containing visual product cards (Image, Price, Buy Button) instead of plain text, significantly improving the user experience and conversion rate.

🛡️ Security & Performance
Security and stability were top priorities during development:

Rate Limiting: Implemented via Flask-Limiter to restrict requests per IP, preventing DDoS attacks and API abuse.

Input Sanitization: Cleans user input to prevent injection attacks and enforces a MAX_INPUT_LENGTH.

Anti-Hallucination: A robust regex mechanism strips unwanted HTML tags or raw code from AI responses to ensure interface integrity.

Environment Variables: Sensitive keys (OpenAI, WooCommerce) are managed via .env files, keeping source code clean and secure.

🛠️ Tech Stack
Backend: Python, Flask

AI & NLP: OpenAI API (GPT-4o-mini) + Custom Prompt Engineering

E-commerce: WooCommerce REST API

Frontend Widget: HTML5, CSS3, Vanilla JS (Embedded Widget)

Utils: Regex, PIL (Image Processing), JSON storage.

📂 Project Structure
Plaintext

├── app.py                 # Main application logic & API endpoints

├── prompts.py             # System prompts & Knowledge base

├── bot_tester.py          # Integration tests & sanity checks

├── widget.html            # Frontend chat interface

├── requirements.txt       # Python dependencies

└── README.md              # Project documentation

🔧 Installation & Setup
Clone the repository:

Bash

git clone https://github.com/alababala-dev/woocommerce-sales-bot.git
cd woocommerce-sales-bot
Install dependencies:

Bash

pip install -r requirements.txt
Configure Environment: Create a .env file and add your keys:


OPENAI_API_KEY=your_key
WC_KEY=your_wc_consumer_key
WC_SECRET=your_wc_consumer_secret
WC_URL=https://your-store.com
Run the application:

Bash

python app.py
👨‍💻 Author
Developed by [alababala-dev] - Full Stack Developer & AI Integrator. Specializing in building smart automation tools that drive business results.

Note: This project is a portfolio demonstration of integrating LLMs with structured E-commerce data.
