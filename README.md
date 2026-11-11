# 🤖 Gemini Python CLI Chatbot

A modular, terminal-based AI chatbot powered by Google Gemini and built with Python. Features real-time response streaming, multi-turn conversation memory, and live token & cost tracking.

---

## ✨ Features

- **⚡ Real-time Streaming**: Responses stream token-by-token directly into your terminal.
- **🧠 Multi-turn Memory**: Retains conversation context across prompts for coherent dialogues.
- **📊 Token & Cost Tracking**: Calculates input/output tokens and estimated dollar cost per request and for the overall session.
- **🛠️ Built-in Commands**: Easily view history, reset conversation context, or check usage statistics on the fly.
- **🔒 Secure Configuration**: Keeps API keys safe using environment variables via `.env`.

---

## 📁 Project Structure

```text
ai-cli-chatbot/
├── chatbot.py          # Handles Gemini API streaming and response handling
├── config.py           # Loads environment variables and pricing configuration
├── history.py          # Manages chat session, system prompts, and conversation history
├── usage.py            # Tracks token consumption and session costs
├── main.py             # CLI entry point and interactive loop
├── requirements.txt    # Project dependencies
├── .env.example        # Template for required environment variables
└── .gitignore          # Prevents sensitive files and virtual envs from being committed
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+** installed
- A **Gemini API Key** (Get one free at [Google AI Studio](https://aistudio.google.com/))

### 1. Clone & Navigate to the Project

```bash
git clone https://github.com/<your-username>/ai-cli-chatbot.git
cd ai-cli-chatbot
```

### 2. Set Up Virtual Environment

On macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

On Windows:
```cmd
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file:
```bash
cp .env.example .env
```

Open `.env` and add your Gemini API Key:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-3.8-flash

# Optional: Set pricing per 1M tokens (USD)
INPUT_PRICE_PER_1M=0.075
OUTPUT_PRICE_PER_1M=0.30
```

---

## 💬 Usage

Start the chatbot by running:

```bash
python main.py
```

### Available Commands

| Command | Description |
| :--- | :--- |
| `/history` | Displays formatted conversation history for the current session. |
| `/reset` | Clears conversation memory and starts a fresh session. |
| `/usage` | Shows total input/output tokens and accumulated session costs. |
| `/exit` | Exits the chatbot application (or press `Ctrl+C`). |

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).

