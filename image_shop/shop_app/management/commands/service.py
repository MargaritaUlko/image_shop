
# service.py
from django.core.management.base import BaseCommand
import pika
from shop_app.consumers import start_consumer
import time

class Command(BaseCommand):
    help = 'Starts the RabbitMQ consumer'
    
    def handle(self, *args, **options):
        while True:
            try:
                start_consumer()
            except pika.exceptions.AMQPConnectionError:
                self.stdout.write('RabbitMQ connection lost, retrying in 5 seconds...')
                time.sleep(5)
            except Exception as e:
                self.stdout.write(f'Error: {e}, retrying in 5 seconds...')
                time.sleep(5)

# import json
# import pika
# import redis
# from django.core.management.base import BaseCommand
# from django.db import transaction
# from django.conf import settings
# from shop_app.models import UserActionEvent

# class Command(BaseCommand):
#     help = 'RabbitMQ consumer with Redis buffering'

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.redis = redis.Redis(
#             host='redis',  # Используем имя сервиса вместо localhost
#             port=6379,
#             db=1,
#             decode_responses=False
#         )
#         self.batch_size = 1000  # Размер пачки для пакетной вставки
#         self.redis_list_key = 'rmq_events_buffer'

#     def handle(self, *args, **options):
#         connection = pika.BlockingConnection(
#             pika.ConnectionParameters(
#                 host='rabbitmq',  # имя сервиса в Docker
#                 port=5672,
#                 credentials=pika.PlainCredentials('admin', 'admin123'),
#                 heartbeat=600
#             )
#         )
#         channel = connection.channel()

#         # Объявляем очередь (если её нет, она создастся)
#         channel.queue_declare(
#             queue='user_actions',
#             durable=True,  # очередь сохранится после перезапуска RabbitMQ
#             exclusive=False,
#             auto_delete=False
#         )

#         def callback(ch, method, properties, body):
#             # logger.info(f"Received: {body.decode()}")
#             ch.basic_ack(delivery_tag=method.delivery_tag)

#         channel.basic_consume(
#             queue='user_actions',
#             on_message_callback=callback,
#             auto_ack=False
#         )

#         # logger.info("Consumer READY. Waiting for messages...")
#         channel.start_consuming()


#         # Подписываемся на очереди
#         for queue in settings.RABBITMQ['QUEUES'].values():
#             channel.basic_consume(
#                 queue=queue,
#                 on_message_callback=callback,
#                 auto_ack=False
#             )

#         self.stdout.write("[*] Waiting for messages. To exit press CTRL+C")
        
#         # Запускаем также периодическую проверку буфера
#         try:
#             while True:
#                 connection.process_data_events(time_limit=1)  # Неблокирующее ожидание
#                 if self.redis.llen(self.redis_list_key) > 0:
#                     self.process_batch(None)
#         except KeyboardInterrupt:
#             connection.close()

#     def process_batch(self, channel):
#         with transaction.atomic():
#             # Получаем пачку сообщений из Redis
#             pipe = self.redis.pipeline()
#             pipe.lrange(self.redis_list_key, 0, self.batch_size - 1)
#             pipe.ltrim(self.redis_list_key, self.batch_size, -1)
#             messages, _ = pipe.execute()

#             if not messages:
#                 return

#             # Подготавливаем объекты для bulk_create
#             events = []
#             for msg in messages:
#                 try:
#                     data = json.loads(msg)
#                     events.append(UserActionEvent(
#                         user_id=data.get('user_id'),
#                         artwork_id=data['artwork_id'],
#                         action_type=data['action_type']
#                     ))
#                 except json.JSONDecodeError as e:
#                     self.stderr.write(f'JSON decode error: {str(e)}')
#                     continue

#             # Пакетная вставка
#             if events:
#                 UserActionEvent.objects.bulk_create(events)
#                 self.stdout.write(f'Processed {len(events)} messages')

#             # Подтверждаем обработку в RabbitMQ
#             if channel:
#                 channel.basic_ack(multiple=True)