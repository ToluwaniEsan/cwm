// backend/main.go — CWM Food Detection API (Go)
// REST API that wraps Google Vision food detection + MealDB recipe lookup
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"strings"

	vision "cloud.google.com/go/vision/apiv1"
	visionpb "google.golang.org/genproto/googleapis/cloud/vision/v1"

	"github.com/gorilla/mux"
	"github.com/joho/godotenv"
	"github.com/rs/cors"
)

// ── Types ─────────────────────────────────────────────────────────────────────

type DetectResponse struct {
	FoodItems []string `json:"food_items"`
}

type Recipe struct {
	ID        string `json:"id"`
	Title     string `json:"title"`
	URL       string `json:"url"`
	Thumbnail string `json:"thumbnail"`
}

type RecipeDetail struct {
	ID           string   `json:"id"`
	Title        string   `json:"title"`
	Category     string   `json:"category"`
	Area         string   `json:"area"`
	Instructions string   `json:"instructions"`
	Thumbnail    string   `json:"thumbnail"`
	YouTube      string   `json:"youtube"`
	Ingredients  []string `json:"ingredients"`
}

// ── Main ──────────────────────────────────────────────────────────────────────

func main() {
	_ = godotenv.Load()

	r := mux.NewRouter()
	r.HandleFunc("/api/detect", detectFoodHandler).Methods("POST")
	r.HandleFunc("/api/recipes", getRecipesHandler).Methods("GET")
	r.HandleFunc("/api/recipes/{id}", getRecipeDetailHandler).Methods("GET")
	r.HandleFunc("/health", healthHandler).Methods("GET")

	handler := cors.New(cors.Options{
		AllowedOrigins: []string{"*"},
		AllowedMethods: []string{"GET", "POST", "OPTIONS"},
		AllowedHeaders: []string{"Content-Type"},
	}).Handler(r)

	port := os.Getenv("PORT")
	if port == "" {
		port = "4000"
	}
	log.Printf("🍽️ CWM API running on :%s", port)
	log.Fatal(http.ListenAndServe(":"+port, handler))
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	respond(w, http.StatusOK, map[string]string{"status": "ok", "service": "cwm-api"})
}

// ── Food Detection ────────────────────────────────────────────────────────────

var foodKeywords = map[string]bool{
	"pizza": true, "burger": true, "hamburger": true, "sushi": true,
	"pasta": true, "salad": true, "sandwich": true, "taco": true,
	"noodle": true, "soup": true, "steak": true, "chicken": true,
	"bread": true, "cake": true, "dessert": true, "fruit": true,
	"vegetable": true, "rice": true, "ramen": true, "curry": true,
	"waffle": true, "pancake": true, "seafood": true, "shrimp": true,
	"salmon": true, "donut": true, "cookie": true, "pie": true,
}

func detectFoodHandler(w http.ResponseWriter, r *http.Request) {
	r.Body = http.MaxBytesReader(w, r.Body, 10<<20) // 10MB limit

	if err := r.ParseMultipartForm(10 << 20); err != nil {
		http.Error(w, `{"error":"image too large or invalid"}`, http.StatusBadRequest)
		return
	}

	file, _, err := r.FormFile("image")
	if err != nil {
		http.Error(w, `{"error":"image field required"}`, http.StatusBadRequest)
		return
	}
	defer file.Close()

	imageBytes, err := io.ReadAll(file)
	if err != nil {
		http.Error(w, `{"error":"failed to read image"}`, http.StatusInternalServerError)
		return
	}

	ctx := context.Background()
	client, err := vision.NewImageAnnotatorClient(ctx)
	if err != nil {
		log.Printf("Vision client error: %v", err)
		http.Error(w, `{"error":"Vision API unavailable"}`, http.StatusInternalServerError)
		return
	}
	defer client.Close()

	img := &visionpb.Image{Content: imageBytes}
	labels, err := client.DetectLabels(ctx, img, nil, 20)
	if err != nil {
		log.Printf("Label detection error: %v", err)
		http.Error(w, `{"error":"Detection failed"}`, http.StatusInternalServerError)
		return
	}

	var foodItems []string
	for _, label := range labels {
		desc := strings.ToLower(label.Description)
		if strings.Contains(desc, "food") || foodKeywords[desc] {
			foodItems = append(foodItems, desc)
		}
	}
	if foodItems == nil {
		foodItems = []string{}
	}

	respond(w, http.StatusOK, DetectResponse{FoodItems: foodItems})
}

// ── Recipes ───────────────────────────────────────────────────────────────────

func getRecipesHandler(w http.ResponseWriter, r *http.Request) {
	items := r.URL.Query()["item"] // ?item=pizza&item=pasta
	if len(items) == 0 {
		http.Error(w, `{"error":"at least one 'item' query param required"}`, http.StatusBadRequest)
		return
	}

	seenIDs := make(map[string]bool)
	var recipes []Recipe

	for _, item := range items {
		apiURL := fmt.Sprintf("https://www.themealdb.com/api/json/v1/1/filter.php?i=%s", url.QueryEscape(item))
		resp, err := http.Get(apiURL)
		if err != nil || resp.StatusCode != 200 {
			continue
		}
		defer resp.Body.Close()

		var data struct {
			Meals []struct {
				IDMeal      string `json:"idMeal"`
				StrMeal     string `json:"strMeal"`
				StrMealThumb string `json:"strMealThumb"`
			} `json:"meals"`
		}
		json.NewDecoder(resp.Body).Decode(&data)

		for _, meal := range data.Meals {
			if seenIDs[meal.IDMeal] {
				continue
			}
			seenIDs[meal.IDMeal] = true
			recipes = append(recipes, Recipe{
				ID:        meal.IDMeal,
				Title:     meal.StrMeal,
				URL:       fmt.Sprintf("https://www.themealdb.com/meal/%s", meal.IDMeal),
				Thumbnail: meal.StrMealThumb,
			})
			if len(recipes) >= 10 {
				break
			}
		}
		if len(recipes) >= 10 {
			break
		}
	}

	if recipes == nil {
		recipes = []Recipe{}
	}
	respond(w, http.StatusOK, recipes)
}

func getRecipeDetailHandler(w http.ResponseWriter, r *http.Request) {
	id := mux.Vars(r)["id"]
	apiURL := fmt.Sprintf("https://www.themealdb.com/api/json/v1/1/lookup.php?i=%s", id)

	resp, err := http.Get(apiURL)
	if err != nil || resp.StatusCode != 200 {
		http.Error(w, `{"error":"recipe not found"}`, http.StatusNotFound)
		return
	}
	defer resp.Body.Close()

	var data struct {
		Meals []map[string]interface{} `json:"meals"`
	}
	json.NewDecoder(resp.Body).Decode(&data)

	if len(data.Meals) == 0 {
		http.Error(w, `{"error":"recipe not found"}`, http.StatusNotFound)
		return
	}

	meal := data.Meals[0]
	str := func(key string) string {
		if v, ok := meal[key]; ok && v != nil {
			return fmt.Sprintf("%v", v)
		}
		return ""
	}

	var ingredients []string
	for i := 1; i <= 20; i++ {
		ing := strings.TrimSpace(str(fmt.Sprintf("strIngredient%d", i)))
		meas := strings.TrimSpace(str(fmt.Sprintf("strMeasure%d", i)))
		if ing != "" {
			ingredients = append(ingredients, strings.TrimSpace(meas+" "+ing))
		}
	}

	detail := RecipeDetail{
		ID:           str("idMeal"),
		Title:        str("strMeal"),
		Category:     str("strCategory"),
		Area:         str("strArea"),
		Instructions: str("strInstructions"),
		Thumbnail:    str("strMealThumb"),
		YouTube:      str("strYoutube"),
		Ingredients:  ingredients,
	}

	respond(w, http.StatusOK, detail)
}

func respond(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(data)
}
