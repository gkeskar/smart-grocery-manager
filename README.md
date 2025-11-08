# 🛒 Smart Grocery List Manager

A multi-store grocery list management application with budget tracking, built with Gradio and Python.

## Features

- **Multi-Store Support**: Manage shopping lists for Trader Joe's, Safeway, and Costco
- **Budget Tracking**: Set individual budgets per store and track overall spending
- **Email Integration**: Send shopping lists via email using Resend API
- **Smart Catalog**: Pre-populated catalogs with real items and prices
- **Interactive UI**: Clean, intuitive Gradio interface

## Installation

```bash
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file with:

```
OPENAI_API_KEY=your_openai_key_here
RESEND_API_KEY=your_resend_key_here
```

## Usage

```bash
python app.py
```

Then open http://localhost:7860 in your browser.

## How to Use

1. **Browse Catalog**: View items available at each store
2. **Add to List**: Click items to add to your shopping list (quantity: 1)
3. **Update Quantity**: Select items and change quantity from dropdown
4. **Track Budget**: Monitor spending per store and overall
5. **Email List**: Send your shopping list to your configured email
6. **Settings**: Configure email address and budgets

## Technologies

- **Gradio**: Web UI framework
- **Pandas**: Data manipulation
- **Resend**: Email service
- **Python-dotenv**: Environment variable management

