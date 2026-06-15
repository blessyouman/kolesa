from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    
    full_name = models.CharField(max_length=255, verbose_name="ФИО")
    phone_number = models.CharField(max_length=50, verbose_name="Контактный телефон")
    avatar_path = models.ImageField(upload_to='avatars/', max_length=255, null=True, blank=True, verbose_name="Путь к аватару")

    class Meta:
        db_table = 'users'  # Жестко привязываем имя таблицы к ТЗ

    def __str__(self):
        return self.username


class Ad(models.Model):
    STATUS_CHOICES = [
        ('active', 'Активно'),
        ('sold', 'Продано'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ads', verbose_name="Продавец")
    brand = models.CharField(max_length=100, verbose_name="Марка")
    model = models.CharField(max_length=100, verbose_name="Модель")
    year = models.IntegerField(verbose_name="Год выпуска")
    price = models.IntegerField(verbose_name="Цена")
    description = models.TextField(null=True, blank=True, verbose_name="Описание")
    image_path = models.ImageField(upload_to='cars/', max_length=255, null=True, blank=True, verbose_name="Фото автомобиля")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="Статус")

    class Meta:
        db_table = 'ads'  # Жестко привязываем имя таблицы к ТЗ

    def __str__(self):
        return f"{self.brand} {self.model} ({self.year})"