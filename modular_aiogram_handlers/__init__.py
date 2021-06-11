class Blueprint:

    def __init__(self):
        self._message_handlers = []

    def message_handler(self, *custom_filters, **kwargs):
        assert(custom_filters or kwargs)

        def deco(callback):
            self._message_handlers.append({
                'callback': callback,
                'custom_filters': custom_filters,
                'kwargs': kwargs,
            })
            return callback
        return deco

    def apply_registration(self, dp):
        for message_handler in self._message_handlers:
            dp.register_message_handler(
                message_handler['callback'],
                *message_handler['custom_filters'],
                **message_handler['kwargs'],
            )
