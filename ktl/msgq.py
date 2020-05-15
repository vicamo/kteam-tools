import json
import pika

# MsgQueue
#
class MsgQueue(object):

    # __init__
    #
    def __init__(s, address='162.213.33.247', exchange='kernel', exchange_type='topic', heartbeat_interval=None, **kwargs):
        s.exchange_name = exchange

        # Address should now be considered deprecated.
        kwargs.setdefault('host', address)
        kwargs.setdefault('port', 5672)
        kwargs.setdefault('connection_attempts', 3)

        # Backwards compatibility with pre-0.11.x pika.
        kwargs.setdefault('heartbeat', heartbeat_interval)

        params = pika.ConnectionParameters(**kwargs)
        s.connection = pika.BlockingConnection(params)
        s.channel = s.connection.channel()
        s.channel.exchange_declare(exchange=s.exchange_name, exchange_type=exchange_type)


    def listen(s, queue_name, routing_key, handler_function, queue_durable=True, queue_arguments=None):
        def wrapped_handler(channel, method, properties, body):
            payload = json.loads(body)
            handler_function(payload)

        s.channel.basic_qos(prefetch_count=1, global_qos=True)

        if isinstance(routing_key, str):
            routing_key = [routing_key]
        s.channel.queue_declare(queue_name, durable=queue_durable, arguments=queue_arguments)
        for key in routing_key:
            s.channel.queue_bind(exchange=s.exchange_name, queue=queue_name, routing_key=key)
        s.channel.basic_consume(queue=queue_name, auto_ack=True, on_message_callback=wrapped_handler)
        s.channel.start_consuming()


    def listen_worker(s, queue_name, routing_key, handler_function, queue_durable=True, auto_delete=False, queue_arguments=None):
        def wrapped_handler(channel, method, properties, body):
            payload = json.loads(body)
            handler_function(payload)
            channel.basic_ack(method.delivery_tag)

        s.channel.basic_qos(prefetch_count=1, global_qos=True)

        if isinstance(routing_key, str):
            routing_key = [routing_key]
        s.channel.queue_declare(queue_name, durable=queue_durable, auto_delete=auto_delete, arguments=queue_arguments)
        for key in routing_key:
            s.channel.queue_bind(exchange=s.exchange_name, queue=queue_name, routing_key=key)
        s.channel.basic_consume(queue=queue_name, auto_ack=False, on_message_callback=wrapped_handler)

    def listen_queues(s, queue_name, routing_key, handler_function, queue_durable=True, auto_delete=False, queue_arguments=None):
        def wrapped_handler(channel, method, properties, body):
            payload = json.loads(body)
            handler_function(payload)
            channel.basic_ack(method.delivery_tag)

        s.channel.basic_qos(prefetch_count=1, global_qos=True)

        if isinstance(routing_key, str):
            routing_key = [routing_key]
        for key in routing_key:
            queue_key = queue_name + '.' + key
            s.channel.queue_declare(queue_key, durable=queue_durable, auto_delete=auto_delete, arguments=queue_arguments)
            s.channel.queue_bind(exchange=s.exchange_name, queue=queue_key, routing_key=key)
            s.channel.basic_consume(queue=queue_key, auto_ack=False, on_message_callback=wrapped_handler)

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

    def exchange_delete(s, queue_name):
        s.channel.exchange_delete(queue_name)

    def publish(s, routing_key, payload, priority=None):
        message_body = json.dumps(payload)
        properties = pika.BasicProperties(delivery_mode=2, priority=priority)
        s.channel.basic_publish(exchange=s.exchange_name, routing_key=routing_key, body=message_body, properties=properties)


class MsgQueueService(MsgQueue):
    """
    Service oriented interface for creating a message queue.  This allows
    us to direct that services appropriatly and choose appropriate
    authentication.  Start with hardwired data.
    """

    # __init__
    #
    def __init__(s, service=None, **kwargs):
        # Services are all on the "new" rabbitmq server by default.
        kwargs.setdefault('host', '10.15.182.2')

        # Use the service prefix for the virtual_host name.
        if '-' in service:
            kwargs.setdefault('virtual_host', service.split('-')[0])

        # The new server always wants a service specific username.  For now
        # there is effectivly no password on those.  We will add this to a
        # configuration service once it is built.
        if 'credentials' not in kwargs:
            kwargs['credentials'] = pika.PlainCredentials(service, service)

        super(MsgQueueService, s).__init__(**kwargs)

# vi:set ts=4 sw=4 expandtab:
