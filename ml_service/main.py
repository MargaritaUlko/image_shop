import json
import os
import pickle
import threading
import time

import pika
import redis as redis_lib
from fastapi import FastAPI

import database
from recommendation_engine import ArtworkRecommender

app = FastAPI(title="ML Recommendation Service")

MODEL_PATH = os.getenv('MODEL_PATH', '/code/image_shop/shop_app/clip-vit-base-patch32')
MEDIA_ROOT = os.getenv('MEDIA_ROOT', '/code/image_shop/media')
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 1))
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'admin')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'admin123')
CACHE_TTL = int(os.getenv('CACHE_TTL', 3600))

redis_client = redis_lib.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

recommender: ArtworkRecommender | None = None


def _cache_set(key: str, value, ttl: int) -> None:
    # Django-redis default key format: ":1:{key}", serialized with pickle
    redis_key = f":1:{key}"
    redis_client.setex(redis_key, ttl, pickle.dumps(value))


def _run_consumer() -> None:
    global recommender

    print("[ML] Loading CLIP model...")
    recommender = ArtworkRecommender(MODEL_PATH)
    print("[ML] Model loaded.")

    # Считаем эмбединги для всех картин без эмбедингов при старте
    all_artworks = database.get_all_artworks()
    missing = [(aid, img) for aid, img in all_artworks if aid not in recommender.artwork_features]
    if missing:
        print(f"[ML] Computing embeddings for {len(missing)} existing artworks at startup...")
        recommender.update_artworks(missing, MEDIA_ROOT)
        print("[ML] Startup embedding computation done.")
    else:
        print("[ML] All artworks already have embeddings.")

    print("[ML] Starting RabbitMQ consumer...")

    while True:
        connection = None
        try:
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
            parameters = pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300,
                connection_attempts=5,
                retry_delay=5,
            )
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            channel.queue_declare(queue='recommendations_tasks', durable=True)
            channel.queue_declare(queue='embedding_tasks', durable=True)
            channel.basic_qos(prefetch_count=1)

            def embedding_callback(ch, method, properties, body):
                try:
                    data = json.loads(body)
                    artwork_id = data['artwork_id']
                    print(f"[ML] Computing embedding for artwork {artwork_id}")

                    artworks = database.get_all_artworks()
                    artwork = [(aid, img) for aid, img in artworks if aid == artwork_id]
                    if artwork:
                        recommender.update_artworks(artwork, MEDIA_ROOT)
                        print(f"[ML] Embedding done for artwork {artwork_id}")
                    else:
                        print(f"[ML] Artwork {artwork_id} not found in DB")

                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as e:
                    print(f"[ML] Error computing embedding for artwork {data.get('artwork_id')}: {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            channel.basic_consume(queue='embedding_tasks', on_message_callback=embedding_callback, auto_ack=False)

            def callback(ch, method, properties, body):
                try:
                    data = json.loads(body)
                    user_id = data['user_id']
                    liked_ids = data['liked_ids']
                    disliked_ids = data['disliked_ids']
                    top_k = data.get('top_k', 8)
                    cache_key = data['cache_key']

                    print(f"[ML] Generating recommendations for user {user_id}")

                    recommended_ids = recommender.get_recommendations(
                        liked_ids=liked_ids,
                        disliked_ids=disliked_ids,
                        top_k=top_k,
                    )

                    _cache_set(cache_key, {
                        'recommended_ids': recommended_ids,
                        'liked_ids': liked_ids,
                        'disliked_ids': disliked_ids,
                    }, CACHE_TTL)

                    print(f"[ML] Done: {len(recommended_ids)} recommendations, key={cache_key}")
                    ch.basic_ack(delivery_tag=method.delivery_tag)

                except Exception as e:
                    import traceback
                    print(f"[ML] Error processing task: {e}")
                    print(traceback.format_exc())
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            channel.basic_consume(queue='recommendations_tasks', on_message_callback=callback, auto_ack=False)
            print('[ML] Waiting for recommendation tasks...')
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError:
            print("[ML] RabbitMQ connection lost, retrying in 5s...")
            time.sleep(5)
        except Exception as e:
            print(f"[ML] Unexpected error: {e}, retrying in 5s...")
            time.sleep(5)
        finally:
            if connection and not connection.is_closed:
                connection.close()


@app.on_event("startup")
def startup():
    thread = threading.Thread(target=_run_consumer, daemon=True)
    thread.start()


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": recommender is not None}
