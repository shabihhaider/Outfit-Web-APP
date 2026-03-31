# OutfitAI — Smart Outfit Recommendation System

OutfitAI is an intelligent fashion assistant that recommends the perfect outfit from your personal wardrobe based on **local weather**, **occasion**, and **color harmony**. 

Built for the Final Year Project (FYP) at **UET Lahore (2022–2026)**.

## 🚀 Key Features

*   **3-Gate Recommendation Engine**:
    *   **Gate 1 (Rules)**: Hard fashion rules (e.g., no hoodies with formal trousers).
    *   **Gate 2 (Occasion)**: Occasion-specific filters (Casual, Formal, Wedding).
    *   **Gate 3 (AI Scoring)**: Weighted scoring using ResNet/EfficientNet embeddings, Color Harmony math, and Weather comfort standards.
*   **Virtual Try-On (VTO)**: Preview how items look on you using AI-powered image generation (Integrated with Hugging Face).
*   **Smart Wardrobe Management**: Automated background removal and color extraction for uploaded items.
*   **Weather Awareness**: Real-time location detection and outfit suggestions matched to thermal comfort (ASHRAE 55).

## 🛠️ Tech Stack

*   **Frontend**: React, Vite, Framer Motion, Tailwind CSS
*   **Backend**: Python, Flask, SQLAlchemy (MySQL/PostgreSQL)
*   **Machine Learning**: TensorFlow, PyTorch, Diffusers
*   **APIs**: OpenWeatherMap, Hugging Face (IDM-VTON)

## 📦 Installation

### 1. Prerequisite
*   Python 3.10+
*   Node.js 18+
*   MySQL (or PostgreSQL)

### 2. Backend Setup
```bash
# Clone the repository
git clone https://github.com/yourusername/outfit-ai.git
cd outfit-ai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your DB credentials and API keys
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## 🔑 Environment Variables

You need the following keys in your `.env` file:
*   `WEATHERAPI_KEY`: Get from OpenWeatherMap.
*   `HF_TOKEN`: Hugging Face token for VTO.
*   `MYSQL_DATABASE_URI`: Your database connection string.
*   `SECRET_KEY`: Flask secret key.

## ⚖️ License
This project is for educational purposes (University FYP). Please refer to the contributors before commercial use.
