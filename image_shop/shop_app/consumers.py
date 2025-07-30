# consumers.py
import pika
import json
import time
import redis

def start_consumer():
    # Подключение к Redis
    redis_client = None
    connection = None
    
    while True:
        try:
            # Подключение к Redis (если еще не подключены)
            if redis_client is None:
                redis_client = redis.StrictRedis(
                    host='redis',
                    port=6379,
                    db=0,
                    decode_responses=True,
                    socket_keepalive=True,
                    health_check_interval=30,
                )
                redis_client.ping()  # Проверка подключения

            # Подключение к RabbitMQ
            credentials = pika.PlainCredentials('admin', 'admin123')
            parameters = pika.ConnectionParameters(
                host='rabbitmq',
                credentials=credentials,
                heartbeat=10,
                blocked_connection_timeout=300,
                connection_attempts=5,
                retry_delay=5
            )
            
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            
            # Создание очереди (если еще не создана)
            channel.queue_declare(queue='button_clicks', durable=True)
            
            # Ограничиваем количество неподтвержденных сообщений
            channel.basic_qos(prefetch_count=1)
            
            def callback(ch, method, properties, body):
                try:
                    data = json.loads(body)
                    print(f"Received message: {data}")
                    
                    # Сохраняем в Redis
                    message_id = data.get("id") or str(method.delivery_tag)
                    redis_key = f"button_click:{message_id}"
                    redis_client.hset(redis_key, mapping=data)
                    redis_client.expire(redis_key, 86400)
                    
                    print(f"Message saved to Redis with key: {redis_key}")
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    
                except json.JSONDecodeError:
                    print("Error: Invalid JSON format")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                except Exception as e:
                    print(f"Error processing message: {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
            channel.basic_consume(
                queue='button_clicks',
                on_message_callback=callback,
                auto_ack=False
            )
            
            print('Waiting for messages...')
            channel.start_consuming()
            
        except pika.exceptions.AMQPConnectionError:
            print("Connection to RabbitMQ lost, reconnecting in 5 seconds...")
            time.sleep(5)
        except redis.ConnectionError:
            print("Connection to Redis lost, reconnecting in 5 seconds...")
            redis_client = None
            time.sleep(5)
        except KeyboardInterrupt:
            print("Consumer stopped by user")
            if connection and not connection.is_closed:
                connection.close()
            break
        except Exception as e:
            print(f"Unexpected error: {e}, retrying in 5 seconds...")
            time.sleep(5)
        finally:
            if connection and not connection.is_closed:
                connection.close()
            connection = None