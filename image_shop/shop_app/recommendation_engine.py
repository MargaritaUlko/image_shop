import os
import numpy as np
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from sklearn.metrics.pairwise import cosine_similarity
from django.core.cache import cache
import joblib
from tqdm import tqdm

class ArtworkRecommender:
    def __init__(self, model_path, use_cache=True):
        self.model = CLIPModel.from_pretrained(model_path, local_files_only=True)
        self.processor = CLIPProcessor.from_pretrained(model_path, local_files_only=True)
        self.features_cache_file = os.path.join(os.path.dirname(model_path), "artwork_features_cache.joblib")
        self.artwork_features = self._load_features_cache()
        self.artwork_ids = list(self.artwork_features.keys()) if self.artwork_features else []
        self.use_cache = use_cache
        self.last_query_vector = None

    def _load_features_cache(self):
        if os.path.exists(self.features_cache_file):
            try:
                return joblib.load(self.features_cache_file)
            except:
                return {}
        return {}

    def _save_features_cache(self):
        joblib.dump(self.artwork_features, self.features_cache_file)

    def _normalize(self, vector):
        """Нормализует вектор по L2 норме"""
        norm = np.linalg.norm(vector)
        if norm < 1e-6:  # Защита от деления на ноль
            return vector
        return vector / norm

    def update_artworks(self, artworks):
        new_artworks = [art for art in artworks if art.id not in self.artwork_features]

        if not new_artworks:
            return

        print(f"Processing {len(new_artworks)} new artworks...")
        for artwork in tqdm(new_artworks, desc="Extracting features"):
            try:
                img = Image.open(artwork.image.path).convert("RGB")
                inputs = self.processor(images=img, return_tensors="pt")
                features = self.model.get_image_features(**inputs).detach().numpy().flatten()
                
                if np.std(features) < 1e-6:
                    print(f"⚠️ WARNING: Artwork {artwork.id} has nearly zero features, skipping.")
                    continue
                
                # Нормализация вектора перед сохранением
                features = self._normalize(features)
                self.artwork_features[artwork.id] = features
            except Exception as e:
                print(f"Error processing artwork {artwork.id}: {str(e)}")

        self.artwork_ids = list(self.artwork_features.keys())
        self._save_features_cache()

    def _compute_query_vector(self, liked_ids, disliked_ids):
        if not liked_ids:
            return None

        pos_vectors = [self.artwork_features[id] for id in liked_ids if id in self.artwork_features]
        neg_vectors = [self.artwork_features[id] for id in disliked_ids if id in self.artwork_features]

        if not pos_vectors:
            return None

        pos_query = np.mean(pos_vectors, axis=0)
        pos_query = self._normalize(pos_query)  # Нормализация среднего вектора лайков

        if neg_vectors:
            neg_query = np.mean(neg_vectors, axis=0)
            neg_query = self._normalize(neg_query)  # Нормализация среднего вектора дизлайков
            final_query = pos_query - 0.5 * neg_query
            final_query = self._normalize(final_query)  # Нормализация итогового вектора
            self.last_query_vector = final_query
            print("✅ Final query vector (with negatives):", final_query[:5])
            return final_query

        self.last_query_vector = pos_query
        print("✅ Final query vector (positive only):", pos_query[:5])
        return pos_query

    def get_recommendations(self, artworks, liked_ids=None, disliked_ids=None, top_k=12):
        liked_ids = liked_ids or []
        disliked_ids = disliked_ids or []

        cache_key = f"recs_{','.join(map(str, liked_ids))}_{','.join(map(str, disliked_ids))}"
        if self.use_cache:
            cached_result = cache.get(cache_key)
            if cached_result:
                print("✅ Used cached result")
                return cached_result

        self.update_artworks(artworks)

        query_vector = self._compute_query_vector(liked_ids, disliked_ids)

        if query_vector is None:
            print("⚠️ Query vector is None. Returning default.")
            default_recs = self.artwork_ids[:top_k]
            if self.use_cache:
                cache.set(cache_key, default_recs, 60 * 15)
            return default_recs

        all_ids = np.array([art_id for art_id in self.artwork_ids if art_id not in liked_ids and art_id not in disliked_ids])
    
    # Если нет картин для рекомендаций (все уже лайкнуты)
        if len(all_ids) == 0:
            return []
        features_matrix = np.array([self.artwork_features[art_id] for art_id in all_ids])
        
        # Нормализация не требуется здесь, так как:
        # 1. Все artwork_features уже нормализованы в update_artworks()
        # 2. query_vector нормализован в _compute_query_vector()
        similarities = cosine_similarity([query_vector], features_matrix)[0]

        top_indices = np.argpartition(-similarities, top_k)[:top_k]
        recommended_ids = all_ids[top_indices].tolist()

        if self.use_cache:
            cache.set(cache_key, recommended_ids, 60 * 15)

        return recommended_ids



# import os
# import numpy as np
# from PIL import Image
# from transformers import CLIPProcessor, CLIPModel
# from sklearn.metrics.pairwise import cosine_similarity

# class ArtworkRecommender:
#     def __init__(self, model_path):
#         self.model = CLIPModel.from_pretrained(model_path, local_files_only=True)
#         self.processor = CLIPProcessor.from_pretrained(model_path, local_files_only=True)
#         self.artwork_features = {}
#         self.artwork_ids = []
#         self.positive_selections = []
#         self.negative_selections = []
#         self.last_query_vector = None

#     def update_artworks(self, artworks):
#         """Обновляет кэш признаков для artworks"""
#         self.artwork_ids = [art.id for art in artworks]
#         for artwork in artworks:
#             if artwork.id not in self.artwork_features:
#                 try:
#                     img = Image.open(artwork.image.path)
#                     inputs = self.processor(images=img, return_tensors="pt")
#                     features = self.model.get_image_features(**inputs).detach().numpy().flatten()
#                     self.artwork_features[artwork.id] = features
#                 except Exception as e:
#                     print(f"Error processing artwork {artwork.id}: {str(e)}")

#     def _compute_query_vector(self):
#         """Вычисляет вектор запроса на основе предпочтений"""
#         if not self.positive_selections:
#             return None
            
#         pos_vectors = [self.artwork_features[art_id] 
#                       for art_id in self.positive_selections 
#                       if art_id in self.artwork_features]
#         if not pos_vectors:
#             return None
            
#         pos_query = np.mean(pos_vectors, axis=0)
        
#         if self.negative_selections:
#             neg_vectors = [self.artwork_features[art_id] 
#                          for art_id in self.negative_selections 
#                          if art_id in self.artwork_features]
#             if neg_vectors:
#                 neg_query = np.mean(neg_vectors, axis=0)
#                 final_query = pos_query - 0.5 * neg_query
#                 self.last_query_vector = final_query
#                 return final_query
        
#         self.last_query_vector = pos_query
#         return pos_query

#     def get_recommendations(self, artworks, liked_ids=None, disliked_ids=None, top_k=12):
#         self.update_artworks(artworks)
        
#         if liked_ids:
#             for art_id in liked_ids:
#                 if art_id not in self.positive_selections:
#                     self.positive_selections.append(art_id)
#                 if art_id in self.negative_selections:
#                     self.negative_selections.remove(art_id)
        
#         if disliked_ids:
#             for art_id in disliked_ids:
#                 if art_id not in self.negative_selections:
#                     self.negative_selections.append(art_id)
#                 if art_id in self.positive_selections:
#                     self.positive_selections.remove(art_id)
        
#         query_vector = self._compute_query_vector()
        
#         if query_vector is None:
#             return []
        
#         features = np.array([self.artwork_features[art_id] for art_id in self.artwork_ids])
#         similarities = cosine_similarity([query_vector], features)[0]
        
#         sorted_indices = np.argsort(similarities)[::-1]
#         sorted_ids = [self.artwork_ids[i] for i in sorted_indices]
        
#         recommended_ids = [
#             art_id for art_id in sorted_ids 
#             if art_id not in self.positive_selections + self.negative_selections
#         ][:top_k]
        
#         return recommended_ids

# MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clip-vit-base-patch32")
# recommender = ArtworkRecommender(MODEL_PATH)