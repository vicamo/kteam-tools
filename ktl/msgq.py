import json
import pika

# MsgQueue
#
class MsgQueue():

    # __init__
    #
    def __init__(s, address='162.213.33.247', port=5672, exchange='kernel', exchange_type='topic'):
        s.exchange_name = exchange

        params = pika.ConnectionParameters(address, port, connection_attempts=3)
        connection = pika.BlockingConnection(params)
        s.channel = connection.channel()
        s.channel.exchange_declare(exchange=s.exchange_name, type=exchange_type)


    def listen(s, queue_name, routing_key, handler_function, queue_durable=True):
        def wrapped_handler(channel, method, properties, body):
            payload = json.loads(body)
            handler_function(payload)

        s.channel.queue_declare(queue_name, durable=queue_durable)
        s.channel.queue_bind(exchange=s.exchange_name, queue=queue_name, routing_key=routing_key)
        s.channel.basic_consume(wrapped_handler, queue=queue_name, no_ack=True)
        s.channel.start_consuming()


    def listen_worker(s, queue_name, routing_key, handler_function, queue_durable=True, auto_delete=False):
        def wrapped_handler(channel, method, properties, body):
            payload = json.loads(body)
            handler_function(payload)
            channel.basic_ack(method.delivery_tag)

        s.channel.queue_declare(queue_name, durable=queue_durable, auto_delete=auto_delete)
        s.channel.queue_bind(exchange=s.exchange_name, queue=queue_name, routing_key=routing_key)
        s.channel.basic_consume(wrapped_handler, queue=queue_name, no_ack=False)
        s.channel.basic_qos(prefetch_count=1)


    def listen_start(s):
        s.channel.start_consuming()


    def listen_stop(s):
        s.channel.stop_consuming()


    def queue_info(s, queue_name):
        res = s.channel.queue_declare(queue=queue_name, passive=True)

        if not res:
            return None

        return {
            'queue':            res.method.queue,
            'consumer_count':   res.method.consumer_count,
            'message_count':    res.method.message_count,
        }


    def queue_delete(s, queue_name):
        s.channel.queue_delete(queue_name)


    def publish(s, routing_key, payload):
        message_body = json.dumps(payload)
        properties = pika.BasicProperties(delivery_mode=2)
        s.channel.basic_publish(exchange=s.exchange_name, routing_key=routing_key, body=message_body, properties=properties)

# vi:set ts=4 sw=4 expandtab:
