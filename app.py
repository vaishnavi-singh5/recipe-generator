import json
import os
import sqlite3
from typing import Dict, List

import streamlit as st
from dotenv import load_dotenv
from google import genai

from recipe_features import authenticate_user, get_saved_recipes, init_db, register_user, save_recipe

load_dotenv()

DB_PATH = os.path.join(os.path.dirname(__file__), "recipe_app.db")
init_db(DB_PATH)
CACHE = {}

try:
    import redis  # type: ignore
except ImportError:  # pragma: no cover
    redis = None

INGREDIENT_NUTRITION: Dict[str, Dict[str, float]] = {
    "rice": {"calories": 130, "protein": 2.7, "carbs": 28.2, "fat": 0.3, "fiber": 0.6},
    "chicken": {"calories": 165, "protein": 31.0, "carbs": 0.0, "fat": 3.6, "fiber": 0.0},
    "egg": {"calories": 72, "protein": 6.3, "carbs": 0.4, "fat": 5.0, "fiber": 0.0},
    "tomato": {"calories": 18, "protein": 0.9, "carbs": 3.9, "fat": 0.2, "fiber": 1.2},
    "tomatoes": {"calories": 18, "protein": 0.9, "carbs": 3.9, "fat": 0.2, "fiber": 1.2},
    "onion": {"calories": 40, "protein": 1.1, "carbs": 9.3, "fat": 0.1, "fiber": 1.7},
    "onions": {"calories": 40, "protein": 1.1, "carbs": 9.3, "fat": 0.1, "fiber": 1.7},
    "garlic": {"calories": 149, "protein": 6.0, "carbs": 33.0, "fat": 0.5, "fiber": 2.4},
    "spinach": {"calories": 23, "protein": 2.9, "carbs": 3.6, "fat": 0.4, "fiber": 2.2},
    "potato": {"calories": 77, "protein": 2.0, "carbs": 17.6, "fat": 0.1, "fiber": 2.2},
    "paneer": {"calories": 265, "protein": 18.0, "carbs": 1.2, "fat": 20.0, "fiber": 0.0},
    "lentils": {"calories": 116, "protein": 9.0, "carbs": 20.0, "fat": 0.4, "fiber": 8.0},
    "broccoli": {"calories": 34, "protein": 2.8, "carbs": 6.6, "fat": 0.4, "fiber": 2.6},
    "olive oil": {"calories": 119, "protein": 0.0, "carbs": 0.0, "fat": 14.0, "fiber": 0.0},
    "pasta": {"calories": 131, "protein": 5.0, "carbs": 25.0, "fat": 1.1, "fiber": 1.8},
    "beans": {"calories": 132, "protein": 9.0, "carbs": 24.0, "fat": 0.5, "fiber": 8.0},
    "cheese": {"calories": 402, "protein": 25.0, "carbs": 1.3, "fat": 33.0, "fiber": 0.0},
    "yogurt": {"calories": 59, "protein": 10.0, "carbs": 3.6, "fat": 0.4, "fiber": 0.0},
    "tofu": {"calories": 144, "protein": 17.0, "carbs": 3.9, "fat": 9.0, "fiber": 1.9},
    "bread": {"calories": 265, "protein": 9.0, "carbs": 49.0, "fat": 3.2, "fiber": 2.7},
    "avocado": {"calories": 160, "protein": 2.0, "carbs": 8.5, "fat": 14.7, "fiber": 6.7},
    "coconut milk": {"calories": 230, "protein": 2.3, "carbs": 2.8, "fat": 24.0, "fiber": 0.0},
    "carrot": {"calories": 41, "protein": 0.9, "carbs": 10.0, "fat": 0.2, "fiber": 2.8},
    "carrots": {"calories": 41, "protein": 0.9, "carbs": 10.0, "fat": 0.2, "fiber": 2.8},
    "soy sauce": {"calories": 10, "protein": 1.0, "carbs": 1.0, "fat": 0.0, "fiber": 0.0},
    "pepper": {"calories": 31, "protein": 1.0, "carbs": 6.0, "fat": 0.3, "fiber": 2.1},
    "mushroom": {"calories": 22, "protein": 3.1, "carbs": 3.3, "fat": 0.3, "fiber": 1.0},
    "coriander": {"calories": 5, "protein": 0.3, "carbs": 0.9, "fat": 0.1, "fiber": 0.5},
    "corn": {"calories": 86, "protein": 3.2, "carbs": 19.0, "fat": 1.2, "fiber": 2.1},
}

INSTANT_RECIPES = {
    "Quick Veggie Stir Fry": {
        "ingredients": ["broccoli", "carrot", "garlic", "soy sauce", "rice"],
        "cuisine": "Chinese",
        "diet": "Vegetarian",
    },
    "Mediterranean Wrap": {
        "ingredients": ["tomato", "onion", "spinach", "avocado", "bread"],
        "cuisine": "Mediterranean",
        "diet": "Vegetarian",
    },
    "Protein Power Bowl": {
        "ingredients": ["chicken", "broccoli", "rice", "olive oil", "garlic"],
        "cuisine": "Fusion",
        "diet": "High Protein",
    },
}


def get_client():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def normalize_ingredients(ingredients_input: str) -> List[str]:
    return [item.strip().lower() for item in ingredients_input.split(",") if item.strip()]


def estimate_nutrition(ingredients: List[str]) -> Dict[str, float]:
    totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0, "fiber": 0.0}
    for ingredient in ingredients:
        normalized = ingredient.strip().lower()
        nutrition = INGREDIENT_NUTRITION.get(normalized)
        if nutrition is None:
            nutrition = INGREDIENT_NUTRITION.get(normalized.split()[0], {})
        for key in totals:
            totals[key] += nutrition.get(key, 0.0)

    servings = max(2, min(4, len(ingredients) // 2 + 1))
    per_serving = {key: round(value / servings, 1) for key, value in totals.items()}
    per_serving["servings"] = float(servings)
    return per_serving


def build_fallback_recipe(ingredients: List[str], cuisine: str, diet: str) -> str:
    title = f"{cuisine} {diet} Stir-Fry"
    ingredient_text = ", ".join(ingredients)
    steps = [
        f"Heat a pan and sauté the main ingredients with a little oil until fragrant.",
        f"Add seasoning, herbs, and any pantry staples that match the {diet.lower()} style.",
        f"Cook until the mixture is tender and serve warm as a quick meal.",
    ]
    return (
        f"### {title}\n\n"
        f"**Ingredients:** {ingredient_text}\n\n"
        f"**Steps:**\n"
        + "\n".join(f"{index}. {step}" for index, step in enumerate(steps, start=1))
    )


def build_cache_key(ingredients: List[str], cuisine: str, diet: str) -> str:
    normalized = ":".join(sorted([ingredient.strip().lower() for ingredient in ingredients if ingredient.strip()]))
    return f"recipe:{normalized}:{cuisine.lower()}:{diet.lower()}"


def get_cached_recipe(cache_key: str):
    cached_value = CACHE.get(cache_key)
    if cached_value is not None:
        return cached_value

    if redis is not None:
        client = getattr(st.session_state, "redis_client", None)
        if client is None:
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                client = redis.Redis.from_url(redis_url, decode_responses=True)
                st.session_state.redis_client = client
        if client is not None:
            raw_value = client.get(cache_key)
            if raw_value:
                try:
                    return json.loads(raw_value)
                except Exception:
                    return raw_value
    return None


def set_cached_recipe(cache_key: str, recipe_text: str) -> None:
    CACHE[cache_key] = recipe_text
    if redis is not None:
        client = getattr(st.session_state, "redis_client", None)
        if client is None:
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                client = redis.Redis.from_url(redis_url, decode_responses=True)
                st.session_state.redis_client = client
        if client is not None:
            client.set(cache_key, json.dumps(recipe_text), ex=3600)


def extract_title(recipe_text: str) -> str:
    lines = [line.strip() for line in recipe_text.splitlines() if line.strip()]
    for line in lines:
        if line.startswith("###"):
            return line.lstrip("#").strip()
    return "Your Recipe"


def generate_recipe(ingredients: List[str], cuisine: str, diet: str) -> str:
    cache_key = build_cache_key(ingredients, cuisine, diet)
    cached_recipe = get_cached_recipe(cache_key)
    if cached_recipe:
        return cached_recipe

    prompt = f"""
    Create a short recipe using these ingredients: {', '.join(ingredients)}.
    Keep it under 120 words.
    Cuisine: {cuisine}
    Diet: {diet}
    Return a title, ingredients list, and 3 short steps.
    """
    client = get_client()
    if client is None:
        result = build_fallback_recipe(ingredients, cuisine, diet)
        set_cached_recipe(cache_key, result)
        return result

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        result = response.text
    except Exception:
        result = build_fallback_recipe(ingredients, cuisine, diet)

    set_cached_recipe(cache_key, result)
    return result


def load_css() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(135deg, #fef9f2 0%, #fffdf9 45%, #f7e8d8 100%);
            color: #23150c;
        }
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 3rem;
        }
        .hero-card {
            background: linear-gradient(135deg, #8b4f1f 0%, #c96b2e 100%);
            border-radius: 24px;
            padding: 1.5rem 1.6rem;
            color: blue;
            box-shadow: 0 12px 30px rgba(139, 79, 31, 0.24);
            margin-bottom: 1rem;
        }
        .hero-card h1 {
            margin-bottom: 0.2rem;
            font-size: 2rem;
            color: #ffffff;
        }
        .hero-card p {
            font-size: 1rem;
            color: #fff7ef;
            opacity: 1;
        }
        .feature-card {
            background: #ffffff;
            border: 1px solid #e6c7a6;
            border-radius: 18px;
            padding: 1rem;
            box-shadow: 0 6px 18px rgba(1,2,3,0.05);
            height: 100%;
            color: #3d2d1f;
        }
        .form-card {
            background: #ffffff;
            border: none;
            border-radius: 18px;
            padding: 1rem 1.1rem;
            margin-bottom: 0.8rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.04);
        }
        .feature-card h3, .feature-card p {
            color: #22150b;
        }
        .recipe-card {
            background: #ffffff;
            border: 1px solid #d8aa76;
            border-radius: 20px;
            padding: 1.2rem 1.3rem;
            box-shadow: 0 8px 24px rgba(0,0,0,0.08);
            margin-top: 0.8rem;
            color: #22150b;
        }
        .stTextInput > div > div > input {
            border-radius: 12px;
            border: 1px solid #000000;
            background: #ffffff;
            color: #000000;
            font-weight: 600;
        }
        .stSelectbox > div > div {
            border-radius: 12px;
            border: 1px solid #000000;
            background: #000000;
            color: #ffffff;
            font-weight: 1000;
        }
        .stSelectbox [data-baseweb="select"] > div,
        .stSelectbox [data-baseweb="select"] > div > div,
        .stSelectbox [role="button"],
        .stSelectbox [role="listbox"],
        .stSelectbox [role="option"] {
            color: #ffffff !important;
            background-color: #000000 !important;
        }
        .stSelectbox [role="option"]:hover {
            background-color: #222222 !important;
            color: #ffffff !important;
        }
        .stButton > button,
        div[data-testid="stFormSubmitButton"] button {
            border-radius: 999px;
            background: linear-gradient(135deg, #8b4f1f 0%, #b5651d 100%);
            color: #ffffff;
            border: 1px solid #8b4f1f;
            padding: 0.5rem 1rem;
            font-weight: 700;
        }
        .stButton > button:hover,
        div[data-testid="stFormSubmitButton"] button:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(184, 95, 43, 0.25);
        }
        [data-testid="stSidebar"] {
            background: #fff7eb;
            color: #1f140d;
        }
        [data-testid="stSidebar"] .st-emotion-cache-1wyi6f9 {
            color: #1f140d;
        }
        [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            color: #1f140d !important;
        }
        .stAlert, .stInfo, .stSuccess, .stWarning {
            border-radius: 14px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(page_title="Recipe Generator", page_icon="🍽️", layout="wide")
load_css()


def main() -> None:
    st.markdown(
        """
        <div class="hero-card">
            <h1>🍽️ Smart Recipe Generator</h1>
            <p>Turn pantry ingredients into delicious meals, discover instant ideas, and see a quick nutrition snapshot in seconds.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([2.1, 1])
    with col_left:
        st.markdown("<div class='feature-card'><h3>✨ Create your perfect dish</h3><p>Enter your ingredients, choose a cuisine, and let the app craft a quick recipe with a nutrition estimate.</p></div>", unsafe_allow_html=True)
    with col_right:
        st.markdown("<div class='feature-card'><h3>⚡ Instant inspiration</h3><p>Pick from ready-made recipe starters and generate something tasty right away.</p></div>", unsafe_allow_html=True)

    with st.sidebar:
        st.header("🍳 Instant recipes")
        st.write("Kick off with a curated starter recipe.")
        preset_name = st.selectbox("Choose a starter idea", list(INSTANT_RECIPES.keys()))
        if st.button("Load instant recipe"):
            preset = INSTANT_RECIPES[preset_name]
            st.session_state["ingredients_input"] = ", ".join(preset["ingredients"])
            st.session_state["cuisine"] = preset["cuisine"]
            st.session_state["diet"] = preset["diet"]
            st.session_state["instant_generated"] = False
            st.success(f"Loaded: {preset_name}")

        if st.button("Generate instant recipe"):
            preset = INSTANT_RECIPES[preset_name]
            st.session_state["ingredients_input"] = ", ".join(preset["ingredients"])
            st.session_state["cuisine"] = preset["cuisine"]
            st.session_state["diet"] = preset["diet"]
            st.session_state["submit_recipe"] = True
            st.session_state["instant_generated"] = True

    with st.form("recipe_form"):
        st.markdown(
            """
            <div class='form-card'>
                <h3 style='margin: 0 0 0.25rem 0; color: #1f140d;'>🧾 Build your recipe</h3>
                <p style='margin: 0; color: #3e2a16;'>Fill in the details below and generate a recipe instantly.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div style='font-size: 1.05rem; font-weight: 700; color: #1f140d; margin-bottom: 0.3rem;'>Ingredients</div>", unsafe_allow_html=True)
        ingredients_input = st.text_input(
            "",
            value=st.session_state.get("ingredients_input", ""),
            placeholder="tomatoes, onions, garlic",
            label_visibility="collapsed",
        )
        st.markdown("<div style='font-size: 1.05rem; font-weight: 700; color: #1f140d; margin-bottom: 0.3rem;'>Cuisine</div>", unsafe_allow_html=True)
        cuisine = st.selectbox(
            "",
            ["Any", "Indian", "Italian", "Mexican", "Chinese", "Japanese", "Mediterranean", "Fusion"],
            index=["Any", "Indian", "Italian", "Mexican", "Chinese", "Japanese", "Mediterranean", "Fusion"].index(
                st.session_state.get("cuisine", "Any")
            ) if st.session_state.get("cuisine", "Any") in ["Any", "Indian", "Italian", "Mexican", "Chinese", "Japanese", "Mediterranean", "Fusion"] else 0,
            label_visibility="collapsed",
        )
        st.markdown("<div style='font-size: 1.05rem; font-weight: 700; color: #1f140d; margin-bottom: 0.3rem;'>Diet</div>", unsafe_allow_html=True)
        diet = st.selectbox(
            "",
            ["Any", "Vegetarian", "Vegan", "Jain", "High Protein"],
            index=["Any", "Vegetarian", "Vegan", "Jain", "High Protein"].index(
                st.session_state.get("diet", "Any")
            ) if st.session_state.get("diet", "Any") in ["Any", "Vegetarian", "Vegan", "Jain", "High Protein"] else 0,
            label_visibility="collapsed",
        )
        st.markdown("<div style='margin-top: 0.6rem;'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button("Generate recipe")

    if submitted or st.session_state.get("submit_recipe"):
        ingredients = normalize_ingredients(ingredients_input)
        if not ingredients:
            st.warning("Please enter at least one ingredient.")
            return

        with st.spinner("Generating your recipe and estimate..."):
            try:
                recipe = generate_recipe(ingredients, cuisine, diet)
                nutrition = estimate_nutrition(ingredients)
                st.session_state["submit_recipe"] = False
            except Exception as exc:
                st.error(f"Something went wrong: {exc}")
                return

        st.markdown("<div class='recipe-card'>", unsafe_allow_html=True)
        st.success("Your recipe is ready!")
        st.markdown(recipe)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style='background: #5a2d0c; color: #ffffff; border-radius: 16px; padding: 1rem 1.1rem; margin-top: 1rem; margin-bottom: 0.8rem;'>
                <h3 style='margin: 0 0 0.4rem 0; color: #ffffff;'>📊 Nutrition estimate</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown(
                f"""
                <div style='background: #000000; color: #ffffff; border-radius: 12px; padding: 0.8rem; text-align: center; margin: 0.2rem 0;'>
                    <div style='font-size: 0.85rem; opacity: 0.8;'>Calories</div>
                    <div style='font-size: 1.1rem; font-weight: 700;'>{nutrition['calories']} kcal</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f"""
                <div style='background: #000000; color: #ffffff; border-radius: 12px; padding: 0.8rem; text-align: center; margin: 0.2rem 0;'>
                    <div style='font-size: 0.85rem; opacity: 0.8;'>Protein</div>
                    <div style='font-size: 1.1rem; font-weight: 700;'>{nutrition['protein']} g</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col3:
            st.markdown(
                f"""
                <div style='background: #000000; color: #ffffff; border-radius: 12px; padding: 0.8rem; text-align: center; margin: 0.2rem 0;'>
                    <div style='font-size: 0.85rem; opacity: 0.8;'>Carbs</div>
                    <div style='font-size: 1.1rem; font-weight: 700;'>{nutrition['carbs']} g</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col4:
            st.markdown(
                f"""
                <div style='background: #000000; color: #ffffff; border-radius: 12px; padding: 0.8rem; text-align: center; margin: 0.2rem 0;'>
                    <div style='font-size: 0.85rem; opacity: 0.8;'>Fat</div>
                    <div style='font-size: 1.1rem; font-weight: 700;'>{nutrition['fat']} g</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col5:
            st.markdown(
                f"""
                <div style='background: #000000; color: #ffffff; border-radius: 12px; padding: 0.8rem; text-align: center; margin: 0.2rem 0;'>
                    <div style='font-size: 0.85rem; opacity: 0.8;'>Fiber</div>
                    <div style='font-size: 1.1rem; font-weight: 700;'>{nutrition['fiber']} g</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.caption(f"Estimated per serving across {int(nutrition['servings'])} servings.")

        if st.session_state.get("instant_generated"):
            st.info("This was generated from your instant recipe preset.")



if __name__ == "__main__":
    main()
