import os
from typing import Dict, List

import streamlit as st
from dotenv import load_dotenv
from google import genai

load_dotenv()

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


def generate_recipe(ingredients: List[str], cuisine: str, diet: str) -> str:
    prompt = f"""
    Create a short recipe using these ingredients: {', '.join(ingredients)}.
    Keep it under 120 words.
    Cuisine: {cuisine}
    Diet: {diet}
    Return a title, ingredients list, and 3 short steps.
    """
    client = get_client()
    if client is None:
        return build_fallback_recipe(ingredients, cuisine, diet)

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text
    except Exception:
        return build_fallback_recipe(ingredients, cuisine, diet)


st.set_page_config(page_title="Recipe Generator", page_icon="🍽️")


def main() -> None:
    st.title("🍽️ Smart Recipe Generator")
    st.write("Create a recipe, get instant ideas, and estimate calories and nutrition in one place.")

    with st.sidebar:
        st.header("⚡ Instant recipes")
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
        ingredients_input = st.text_input(
            "Ingredients",
            value=st.session_state.get("ingredients_input", ""),
            placeholder="tomatoes, onions, garlic",
        )
        cuisine = st.selectbox(
            "Cuisine",
            ["Any", "Indian", "Italian", "Mexican", "Chinese", "Japanese", "Mediterranean", "Fusion"],
            index=["Any", "Indian", "Italian", "Mexican", "Chinese", "Japanese", "Mediterranean", "Fusion"].index(
                st.session_state.get("cuisine", "Any")
            ) if st.session_state.get("cuisine", "Any") in ["Any", "Indian", "Italian", "Mexican", "Chinese", "Japanese", "Mediterranean", "Fusion"] else 0,
        )
        diet = st.selectbox(
            "Diet",
            ["Any", "Vegetarian", "Vegan", "Jain", "High Protein"],
            index=["Any", "Vegetarian", "Vegan", "Jain", "High Protein"].index(
                st.session_state.get("diet", "Any")
            ) if st.session_state.get("diet", "Any") in ["Any", "Vegetarian", "Vegan", "Jain", "High Protein"] else 0,
        )
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

        st.success("Here is your recipe:")
        st.markdown(recipe)

        st.subheader("📊 Nutrition estimate")
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Calories", f"{nutrition['calories']} kcal")
        col2.metric("Protein", f"{nutrition['protein']} g")
        col3.metric("Carbs", f"{nutrition['carbs']} g")
        col4.metric("Fat", f"{nutrition['fat']} g")
        col5.metric("Fiber", f"{nutrition['fiber']} g")

        st.caption(f"Estimated per serving across {int(nutrition['servings'])} servings.")

        if st.session_state.get("instant_generated"):
            st.info("This was generated from your instant recipe preset.")


if __name__ == "__main__":
    main()
