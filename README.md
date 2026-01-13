# 🛒 Smart Grocery List Manager

A multi-store grocery list management application with AI-powered assistant, budget tracking, and seamless cloud sync.

## ✨ Features

### 🤖 AI Assistant (NEW!)
- **Natural Language Chat**: Ask questions like "Show me frozen items in TJ" or "Add milk to my list"
- **Conversation Memory**: AI remembers your previous messages for context
- **Quick Actions**: One-click buttons for common tasks
- **Smart Tool Calling**: Powered by DeepSeek for reliable function execution

### 🛍️ Multi-Store Support
- Manage shopping lists for Trader Joe's, Safeway, Costco, and Indian Groceries
- Store-specific catalogs with real items and prices
- Switch between stores seamlessly

### 💰 Budget Tracking
- Set individual budgets per store
- Track overall spending across all stores
- Visual budget indicators

### 📧 Email Integration
- Send shopping lists via email using Resend API
- Share lists with family members

### ☁️ Cloud Sync
- Automatic sync to HuggingFace Hub
- Access your lists from anywhere

## 🚀 Installation

```bash
pip install -r requirements.txt
```

## 🔐 Environment Variables

Create a `.env` file with:

```env
# Required for AI Assistant
DEEPSEEK_API_KEY=your_deepseek_key_here

# Optional fallbacks for AI
GROQ_API_KEY=your_groq_key_here
GOOGLE_API_KEY=your_google_key_here

# For email functionality
RESEND_API_KEY=your_resend_key_here

# For cloud sync
HF_TOKEN=your_huggingface_token_here
```

## 📖 Usage

```bash
python app.py
```

Then open http://localhost:7860 in your browser.

## 🎯 How to Use

### Using the AI Assistant
1. Go to the **🤖 AI Chat** tab
2. Type naturally: "Show me my shopping list" or "Search for organic milk"
3. Use quick action buttons for common tasks
4. The AI remembers your conversation!

### Manual Shopping
1. **Browse Catalog**: View items available at each store
2. **Add to List**: Click items to add to your shopping list
3. **Update Quantity**: Use +/- buttons or dropdown
4. **Track Budget**: Monitor spending per store
5. **Email List**: Send your list to configured email

## 🏗️ Architecture

```
app.py                 # Gradio UI with AI Chat tab
├── grocery_app.py     # Core GroceryManager class
├── grocery_agents.py  # AI Agent system (catalog + shopping tools)
└── grocery_catalog.json  # Store catalogs
```

## 🤖 AI Agent System

The AI assistant uses the OpenAI Agents SDK with:

| Component | Purpose |
|-----------|---------|
| **Catalog Tools** | Search, add, delete catalog items |
| **Shopping Tools** | Add/remove from list, check budget |
| **Conversation History** | Remember context across messages |
| **Smart Cache** | Fast responses for repeated queries |

## 🛠️ Technologies

- **Gradio**: Web UI framework
- **OpenAI Agents SDK**: AI agent orchestration
- **DeepSeek**: LLM for function calling
- **HuggingFace Hub**: Cloud storage
- **Resend**: Email service
- **Pandas**: Data manipulation

## 🔗 Links

- **Live Demo**: [HuggingFace Space](https://huggingface.co/spaces/gandhalikeskar/smart-grocery-manager)
- **Repository**: [GitHub](https://github.com/gkeskar/smart-grocery-manager)

## 📄 License

MIT License

## About

Smart Grocery List Manager - Multi-store shopping app with AI assistant and budget tracking
