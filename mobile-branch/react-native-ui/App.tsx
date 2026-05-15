// mobile-branch/react-native-ui/App.tsx — CWM Mobile
// Food Detection & Recipe Finder
// Run with: npx expo start

import React, { useState, useCallback } from 'react';
import {
  View, Text, TouchableOpacity, ScrollView, Image,
  StyleSheet, StatusBar, ActivityIndicator, FlatList,
  SafeAreaView, Alert, Platform,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';

const API_BASE = 'http://localhost:4000';

// ─── Theme ────────────────────────────────────────────────────────────────────
const C = {
  bg: '#0f1117',
  surface: '#1e2029',
  surface2: '#2a2d3a',
  border: '#2a2d3a',
  text: '#e8eaf2',
  muted: '#6b7094',
  accent: '#6c63ff',
  green: '#06d6a0',
  red: '#ff4d6d',
};

// ─── Types ───────────────────────────────────────────────────────────────────
interface Recipe {
  id: string;
  title: string;
  url: string;
  thumbnail: string;
}

interface RecipeDetail {
  id: string;
  title: string;
  category: string;
  area: string;
  instructions: string;
  thumbnail: string;
  youtube: string;
  ingredients: string[];
}

type Screen = 'home' | 'recipes' | 'detail';

// ─── Root App ─────────────────────────────────────────────────────────────────
export default function App() {
  const [screen, setScreen] = useState<Screen>('home');
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [detectedFood, setDetectedFood] = useState<string[]>([]);
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [selectedDetail, setSelectedDetail] = useState<RecipeDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('');

  // ── Image Picker ────────────────────────────────────────────────────────────
  const pickImage = useCallback(async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission required', 'Camera roll access is needed to pick images.');
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      quality: 0.8,
    });
    if (!result.canceled && result.assets[0]) {
      setImageUri(result.assets[0].uri);
      setDetectedFood([]);
      setRecipes([]);
      setStatus('');
    }
  }, []);

  const takePhoto = useCallback(async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission required', 'Camera access is needed to take photos.');
      return;
    }
    const result = await ImagePicker.launchCameraAsync({
      allowsEditing: true,
      quality: 0.8,
    });
    if (!result.canceled && result.assets[0]) {
      setImageUri(result.assets[0].uri);
      setDetectedFood([]);
      setRecipes([]);
      setStatus('');
    }
  }, []);

  // ── Detect Food ─────────────────────────────────────────────────────────────
  const detectFood = useCallback(async () => {
    if (!imageUri) return;
    setLoading(true);
    setStatus('Analyzing image…');

    try {
      const formData = new FormData();
      formData.append('image', {
        uri: imageUri,
        name: 'food.jpg',
        type: 'image/jpeg',
      } as any);

      const res = await fetch(`${API_BASE}/api/detect`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      const food: string[] = data.food_items || [];

      if (food.length === 0) {
        setStatus('No food detected. Try a clearer photo.');
        setLoading(false);
        return;
      }

      setDetectedFood(food);
      setStatus(`Detected: ${food.join(', ')}`);

      // Fetch recipes
      setStatus('Finding recipes…');
      const itemParams = food.map(f => `item=${encodeURIComponent(f)}`).join('&');
      const recipeRes = await fetch(`${API_BASE}/api/recipes?${itemParams}`);
      const recipeData: Recipe[] = await recipeRes.json();

      setRecipes(recipeData);
      setScreen('recipes');
    } catch (e) {
      Alert.alert('Error', 'Failed to connect to the CWM API. Make sure it is running.');
    } finally {
      setLoading(false);
    }
  }, [imageUri]);

  // ── Load Recipe Detail ──────────────────────────────────────────────────────
  const loadDetail = useCallback(async (recipe: Recipe) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/recipes/${recipe.id}`);
      const detail: RecipeDetail = await res.json();
      setSelectedDetail(detail);
      setScreen('detail');
    } catch {
      Alert.alert('Error', 'Could not load recipe details.');
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <SafeAreaView style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor={C.bg} />

      {/* Header */}
      <View style={styles.header}>
        {screen !== 'home' && (
          <TouchableOpacity onPress={() => setScreen(screen === 'detail' ? 'recipes' : 'home')} style={styles.backBtn}>
            <Text style={styles.backText}>← Back</Text>
          </TouchableOpacity>
        )}
        <Text style={styles.headerTitle}>🍽️ CWM Food Finder</Text>
      </View>

      {/* Screens */}
      {screen === 'home' && (
        <HomeScreen
          imageUri={imageUri}
          detectedFood={detectedFood}
          status={status}
          loading={loading}
          onPickImage={pickImage}
          onTakePhoto={takePhoto}
          onDetect={detectFood}
        />
      )}
      {screen === 'recipes' && (
        <RecipesScreen recipes={recipes} detectedFood={detectedFood} onSelect={loadDetail} loading={loading} />
      )}
      {screen === 'detail' && selectedDetail && (
        <DetailScreen detail={selectedDetail} />
      )}
    </SafeAreaView>
  );
}

// ─── Home Screen ──────────────────────────────────────────────────────────────
function HomeScreen({ imageUri, status, loading, onPickImage, onTakePhoto, onDetect }: any) {
  return (
    <ScrollView contentContainerStyle={styles.screenPad} showsVerticalScrollIndicator={false}>
      <Text style={styles.screenTitle}>Snap or Upload Food</Text>
      <Text style={styles.screenSub}>We'll identify what it is and find you recipes to make it yourself.</Text>

      {/* Image Preview */}
      {imageUri ? (
        <Image source={{ uri: imageUri }} style={styles.imagePreview} resizeMode="cover" />
      ) : (
        <View style={styles.imagePlaceholder}>
          <Text style={styles.imagePlaceholderText}>📷{'\n'}No image selected</Text>
        </View>
      )}

      {/* Pick Buttons */}
      <View style={styles.btnRow}>
        <TouchableOpacity style={[styles.btn, styles.btnOutline]} onPress={onPickImage}>
          <Text style={styles.btnOutlineText}>📂 Gallery</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.btn, styles.btnOutline]} onPress={onTakePhoto}>
          <Text style={styles.btnOutlineText}>📷 Camera</Text>
        </TouchableOpacity>
      </View>

      {/* Detect Button */}
      {imageUri && (
        <TouchableOpacity
          style={[styles.btn, styles.btnPrimary, loading && styles.btnDisabled]}
          onPress={onDetect}
          disabled={loading}
        >
          {loading
            ? <ActivityIndicator color="white" />
            : <Text style={styles.btnPrimaryText}>🔍 Detect Food & Get Recipes</Text>
          }
        </TouchableOpacity>
      )}

      {/* Status */}
      {status !== '' && (
        <Text style={styles.statusText}>{status}</Text>
      )}

      {/* How it works */}
      <View style={styles.howItWorks}>
        <Text style={styles.howTitle}>How it works</Text>
        {[
          '📸 Upload or take a photo of any food',
          '🤖 AI identifies the food items',
          '🍳 Recipes are fetched automatically',
          '📋 Get full ingredients + instructions',
        ].map((step, i) => (
          <Text key={i} style={styles.howStep}>{step}</Text>
        ))}
      </View>
    </ScrollView>
  );
}

// ─── Recipes Screen ───────────────────────────────────────────────────────────
function RecipesScreen({ recipes, detectedFood, onSelect, loading }: any) {
  return (
    <View style={{ flex: 1 }}>
      <View style={styles.screenPad}>
        <Text style={styles.screenTitle}>Recipes Found</Text>
        <View style={styles.tagRow}>
          {detectedFood.map((f: string, i: number) => (
            <View key={i} style={styles.tag}><Text style={styles.tagText}>🍴 {f}</Text></View>
          ))}
        </View>
      </View>
      {loading ? (
        <View style={styles.center}><ActivityIndicator color={C.accent} size="large" /></View>
      ) : (
        <FlatList
          data={recipes}
          keyExtractor={r => r.id}
          contentContainerStyle={{ padding: 16 }}
          ListEmptyComponent={<Text style={styles.emptyText}>No recipes found. Try a different image.</Text>}
          renderItem={({ item }) => (
            <TouchableOpacity style={styles.recipeCard} onPress={() => onSelect(item)}>
              {item.thumbnail ? (
                <Image source={{ uri: item.thumbnail }} style={styles.recipeThumb} />
              ) : (
                <View style={[styles.recipeThumb, { backgroundColor: C.surface2, alignItems: 'center', justifyContent: 'center' }]}>
                  <Text style={{ fontSize: 24 }}>🍽️</Text>
                </View>
              )}
              <View style={styles.recipeInfo}>
                <Text style={styles.recipeTitle}>{item.title}</Text>
                <Text style={styles.recipeLink}>Tap for full recipe →</Text>
              </View>
            </TouchableOpacity>
          )}
        />
      )}
    </View>
  );
}

// ─── Detail Screen ────────────────────────────────────────────────────────────
function DetailScreen({ detail }: { detail: RecipeDetail }) {
  return (
    <ScrollView contentContainerStyle={styles.screenPad} showsVerticalScrollIndicator={false}>
      {detail.thumbnail && (
        <Image source={{ uri: detail.thumbnail }} style={styles.detailImage} resizeMode="cover" />
      )}
      <Text style={styles.screenTitle}>{detail.title}</Text>
      <Text style={styles.detailMeta}>
        {detail.category && `${detail.category}`}{detail.area && ` · ${detail.area}`}
      </Text>

      {detail.ingredients.length > 0 && (
        <>
          <Text style={styles.sectionLabel}>INGREDIENTS</Text>
          {detail.ingredients.map((ing, i) => (
            <View key={i} style={styles.ingredientRow}>
              <Text style={styles.ingredientBullet}>·</Text>
              <Text style={styles.ingredientText}>{ing}</Text>
            </View>
          ))}
        </>
      )}

      {detail.instructions && (
        <>
          <Text style={styles.sectionLabel}>INSTRUCTIONS</Text>
          <Text style={styles.instructions}>{detail.instructions}</Text>
        </>
      )}
    </ScrollView>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────
const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderColor: C.border,
    gap: 12,
  },
  backBtn: { padding: 4 },
  backText: { color: C.accent, fontSize: 14, fontWeight: '600' },
  headerTitle: { color: C.accent, fontSize: 17, fontWeight: '800' },

  screenPad: { padding: 20 },
  screenTitle: { color: C.text, fontSize: 22, fontWeight: '800', marginBottom: 6 },
  screenSub: { color: C.muted, fontSize: 14, marginBottom: 20, lineHeight: 20 },
  sectionLabel: { color: C.muted, fontSize: 11, fontWeight: '700', letterSpacing: 1.2, marginTop: 20, marginBottom: 10 },
  emptyText: { color: C.muted, fontSize: 14, textAlign: 'center', marginTop: 40 },

  imagePreview: { width: '100%', height: 220, borderRadius: 12, marginBottom: 16 },
  imagePlaceholder: {
    width: '100%', height: 220, borderRadius: 12, marginBottom: 16,
    backgroundColor: C.surface, borderWidth: 1, borderColor: C.border,
    borderStyle: 'dashed', alignItems: 'center', justifyContent: 'center',
  },
  imagePlaceholderText: { color: C.muted, textAlign: 'center', lineHeight: 28, fontSize: 14 },

  btnRow: { flexDirection: 'row', gap: 10, marginBottom: 12 },
  btn: { flex: 1, borderRadius: 10, padding: 13, alignItems: 'center', justifyContent: 'center' },
  btnPrimary: { backgroundColor: C.accent, marginBottom: 16 },
  btnPrimaryText: { color: 'white', fontWeight: '700', fontSize: 15 },
  btnOutline: { backgroundColor: C.surface, borderWidth: 1, borderColor: C.border },
  btnOutlineText: { color: C.text, fontWeight: '600', fontSize: 14 },
  btnDisabled: { opacity: 0.5 },

  statusText: { color: C.green, fontSize: 13, fontWeight: '500', marginBottom: 16, textAlign: 'center' },

  howItWorks: { backgroundColor: C.surface, borderRadius: 12, padding: 16, marginTop: 8 },
  howTitle: { color: C.text, fontSize: 14, fontWeight: '700', marginBottom: 10 },
  howStep: { color: C.muted, fontSize: 13, lineHeight: 24 },

  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 4 },
  tag: { backgroundColor: C.surface, borderRadius: 20, paddingHorizontal: 12, paddingVertical: 5, borderWidth: 1, borderColor: C.accent },
  tagText: { color: C.accent, fontSize: 12, fontWeight: '600' },

  recipeCard: { flexDirection: 'row', backgroundColor: C.surface, borderRadius: 10, marginBottom: 10, overflow: 'hidden', borderWidth: 1, borderColor: C.border },
  recipeThumb: { width: 80, height: 80 },
  recipeInfo: { flex: 1, padding: 12, justifyContent: 'center' },
  recipeTitle: { color: C.text, fontSize: 14, fontWeight: '600', marginBottom: 4 },
  recipeLink: { color: C.accent, fontSize: 12 },

  detailImage: { width: '100%', height: 200, borderRadius: 12, marginBottom: 16 },
  detailMeta: { color: C.muted, fontSize: 13, marginBottom: 4 },
  ingredientRow: { flexDirection: 'row', gap: 8, marginBottom: 6 },
  ingredientBullet: { color: C.accent, fontSize: 16, lineHeight: 20 },
  ingredientText: { color: C.text, fontSize: 14, flex: 1, lineHeight: 20 },
  instructions: { color: C.text, fontSize: 14, lineHeight: 22 },

  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
});
