import os
import numpy as np
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm

import database


class ArtworkRecommender:
    def __init__(self, model_path: str):
        self.model = CLIPModel.from_pretrained(model_path, local_files_only=True)
        self.processor = CLIPProcessor.from_pretrained(model_path, local_files_only=True)
        self.artwork_features: dict = database.load_embeddings()
        self.artwork_ids: list = list(self.artwork_features.keys())

    def _normalize(self, vector):
        norm = np.linalg.norm(vector)
        return vector if norm < 1e-6 else vector / norm

    def update_artworks(self, artworks: list[tuple[int, str]], media_root: str) -> None:
        """artworks: list of (id, image_relative_path)"""
        new_artworks = [(aid, img) for aid, img in artworks if aid not in self.artwork_features]
        if not new_artworks:
            return

        print(f"[ML] Processing {len(new_artworks)} new artworks...")
        for artwork_id, image_path in tqdm(new_artworks, desc="Extracting features"):
            try:
                full_path = os.path.join(media_root, image_path)
                img = Image.open(full_path).convert("RGB")
                inputs = self.processor(images=img, return_tensors="pt")
                features = self.model.get_image_features(**inputs).detach().numpy().flatten()

                if np.std(features) < 1e-6:
                    print(f"[ML] WARNING: artwork {artwork_id} has near-zero features, skipping.")
                    continue

                features = self._normalize(features)
                self.artwork_features[artwork_id] = features
                database.save_embedding(artwork_id, features)

            except Exception as e:
                print(f"[ML] Error processing artwork {artwork_id}: {e}")

        self.artwork_ids = list(self.artwork_features.keys())

    def _compute_query_vector(self, liked_ids: list, disliked_ids: list):
        pos_vectors = [self.artwork_features[i] for i in liked_ids if i in self.artwork_features]
        if not pos_vectors:
            return None

        pos_query = self._normalize(np.mean(pos_vectors, axis=0))

        neg_vectors = [self.artwork_features[i] for i in disliked_ids if i in self.artwork_features]
        if neg_vectors:
            neg_query = self._normalize(np.mean(neg_vectors, axis=0))
            return self._normalize(pos_query - 0.5 * neg_query)

        return pos_query

    def get_recommendations(
        self,
        liked_ids: list = None,
        disliked_ids: list = None,
        top_k: int = 12,
    ) -> list:
        liked_ids = liked_ids or []
        disliked_ids = disliked_ids or []

        query_vector = self._compute_query_vector(liked_ids, disliked_ids)
        if query_vector is None:
            return self.artwork_ids[:top_k]

        candidate_ids = np.array([
            aid for aid in self.artwork_ids
            if aid not in liked_ids and aid not in disliked_ids
        ])
        if len(candidate_ids) == 0:
            return []

        features_matrix = np.array([self.artwork_features[aid] for aid in candidate_ids])
        similarities = cosine_similarity([query_vector], features_matrix)[0]

        top_k = min(top_k, len(candidate_ids))
        top_indices = np.argpartition(-similarities, top_k)[:top_k]
        return candidate_ids[top_indices].tolist()
