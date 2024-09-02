import random
from telegram.ext import CallbackContext


class CacheService:
    def get(self, key: str, context: CallbackContext) -> dict:
        if key == 'city_forecast' or key == 'city_facts' or key == 'city_tips':
            return context.user_data.get(key)
        
        if key in context.user_data:
            copied_data = context.user_data.get(key)[:]
            random.shuffle(copied_data)
            random_items = copied_data[:7]

            return random_items
        return {}

    def set(self, key: str, value: list, context: CallbackContext):
        context.user_data[key] = value

    def delete(self, key: str, context: CallbackContext):
        if key in context.user_data:
            del context.user_data[key]

    def clear(self):
        self.cache.clear()

    def randomize(self, key: str, context: CallbackContext):
        pass
