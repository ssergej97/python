import uuid

from django.core.mail import send_mail

from shared.cache import CacheService
from users.models import User


class ActivationService:
    UUID_NAMESPACE = uuid.uuid4()

    def __init__(self, email: str):
        self.email: str | None = None
        self.cache: CacheService = CacheService()

    def create_activation_key(self):
        # key = uuid.uuid3(
        #     self.UUID_NAMESPACE,
        #     self.email
        # )
        return uuid.uuid4()

    def save_activation_information(self, user_id: int, activation_key: str):
        """
        Save activation info to the cache
        :param user_id:
        :param activation_key:
        :return:
        """

        payload = {"user_id": user_id}

        self.cache.set(namespace="activation", key=str(activation_key), value=payload, ttl=800)

        return None

    def send_user_activation_email(self, activation_key: str):
        if self.email is None:
            raise ValueError(f"No email specified for user activation process")
        # SMTP Client send email request
        activation_link = f"https://frontend.catering.com/activation/{activation_key}"
        send_mail(
            subject="User Activation",
            message=f"Please activate your account: {activation_link}",
            from_email="admin@catering.com",
            recipient_list=[self.email],
        )

    def activate_user(self, activation_key: str) -> None:
        user_cache_payload : dict | None = self.cache.get(namespace="activation", key=activation_key)

        if user_cache_payload is None:
            raise ValueError("No payload in cache")

        user = User.objects.get(id=user_cache_payload["user_id"])
        user.is_active = True
        user.save()

