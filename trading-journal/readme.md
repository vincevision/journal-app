# SMC Trading Journal 📊

A web-based trading journal built for Smart Money Concepts (SMC/ICT) traders. 
Log trades with full SMC methodology tracking, upload screenshots, get AI-powered 
analysis via Groq, and generate professional PDF reports.

## Features

- **Full SMC Workflow**: HTF bias → POI identification → LTF confirmation → Entry
- **Screenshot Management**: Upload and organize trade screenshots with labels
- **AI Analysis**: Groq-powered trade review using Llama 3.3 70B
- **PDF Reports**: Professional PDF output with all trade data and screenshots
- **Auto-Organization**: Trades sorted into winning/losing/missed folders
- **Dashboard**: Win rate, P&L tracking, R:R statistics
- **Dark Theme**: Easy on the eyes for late-night chart sessions

## Setup

### 1. Clone & Install

```bash
git clone https://github.com/yourusername/trading-journal.git
cd trading-journal
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
pip install -r requirements.txt