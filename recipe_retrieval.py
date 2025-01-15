import requests

URL = "https://www.themealdb.com/api/json/v1/1/filter.php"

def get_recipes(food_items):
    recipes = []
    for item in food_items:
        params = {"i": item}  # Search by ingredient
        response = requests.get(URL, params=params)
        if response.status_code == 200:
            meals = response.json().get("meals")
            if meals:  # Ensure `meals` is not None
                recipes.extend([
                    {"title": meal["strMeal"], "url": f"https://www.themealdb.com/meal/{meal['idMeal']}"}
                    for meal in meals
                ])
            else:
                print(f"No recipes found for {item}.")
        else:
            print(f"Error fetching recipes for {item}: {response.status_code}")
    return recipes[:5]  # Return top 5 recipes

