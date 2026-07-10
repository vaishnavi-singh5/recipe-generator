# Smart Recipe Generator

A simple Streamlit app that helps you generate recipe ideas, explore instant recipe presets, and estimate nutrition values such as calories, protein, carbs, fat, and fiber.

## Features
- Generate a recipe from custom ingredients
- Choose cuisine and diet preferences
- Use instant recipe presets for quick ideas
- Estimate nutrition per serving
- Fallback recipe generation works even if the Gemini API key is not configured

## Requirements
Install the required packages:

```bash
pip install -r requirements.txt
```

## Run the app
```bash
streamlit run app.py
```

Then open the local URL shown in the terminal, usually:

```text
http://localhost:8501
```

## Environment variable
If you want AI-generated recipes through Google Gemini, add your API key to a `.env` file:

```env
GOOGLE_API_KEY=your_api_key_here
```
