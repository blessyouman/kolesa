from datetime import datetime
import os

from django.conf import settings  # Импортируем настройки
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.shortcuts import redirect, render

# Безопасно достаем BASE_DIR из конфигурации Django
BASE_DIR = settings.BASE_DIR

# Вспомогательная функция для получения сессии
def get_current_user(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    with connection.cursor() as cursor:
        cursor.execute('SELECT id, username, full_name, phone_number, avatar_path FROM users WHERE id = %s', [user_id])
        row = cursor.fetchone()
        if row:
            return {
                'id': row[0], 
                'username': row[1], 
                'full_name': row[2], 
                'phone_number': row[3], 
                'avatar_path': row[4]
            }
        return None

# 1. Регистрация
def register_view(request):
    if request.method != 'POST':
        return render(request, 'register.html')
        
    username = request.POST.get('username')
    password = request.POST.get('password')
    full_name = request.POST.get('full_name')
    phone_number = request.POST.get('phone_number')
    
    if not all([username, password, full_name, phone_number]):
        messages.error(request, "Все поля обязательны для заполнения.")
        return render(request, 'register.html')
        
    with connection.cursor() as cursor:
        cursor.execute('SELECT id FROM users WHERE username = %s', [username])
        if cursor.fetchone():
            messages.error(request, "Этот логин уже занят.")
            return render(request, 'register.html')
            
        cursor.execute(
            'INSERT INTO users (username, password, full_name, phone_number, avatar_path, first_name, last_name, email, is_superuser, is_staff, is_active, date_joined) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id',
            [username, make_password(password), full_name, phone_number, '', '', '', '', False, False, True, datetime.now()]
        )
        request.session['user_id'] = cursor.fetchone()[0]
        
    return redirect('cars')

# 2. Вход
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password_input = request.POST.get('password')

        with connection.cursor() as cursor:
            cursor.execute('SELECT id, password FROM users WHERE username = %s', [username])
            row = cursor.fetchone()

        if row:
            user_id, hashed_password = row
            if check_password(password_input, hashed_password):
                request.session['user_id'] = user_id
                return redirect('cars')
            else:
                return render(request, 'login.html', {'error': 'Неверный пароль'})
        else:
            return render(request, 'login.html', {'error': 'Пользователь не найден'})

    return render(request, 'login.html')

# Выход
def logout_view(request):
    request.session.pop('user_id', None)
    return redirect('cars')

# 3. Главная: Объявления (Фильтрация, Сортировка, Поиск)
def cars_view(request):
    brand = request.GET.get('brand', '').strip()
    year_from = request.GET.get('year_from', '').strip()
    year_to = request.GET.get('year_to', '').strip()
    sort = request.GET.get('sort', '').strip()
    
    query = """
        SELECT a.id, a.brand, a.model, a.year, a.price, a.description, a.image_path, u.phone_number 
        FROM ads a 
        JOIN users u ON a.user_id = u.id 
        WHERE a.status = 'active'
    """
    params = []
    
    if brand:
        query += " AND a.brand ILIKE %s"
        params.append(f"%{brand}%")
    if year_from:
        query += " AND a.year >= %s"
        params.append(int(year_from))
    if year_to:
        query += " AND a.year <= %s"
        params.append(int(year_to))
        
    if sort == 'asc':
        query += " ORDER BY a.price ASC"
    elif sort == 'desc':
        query += " ORDER BY a.price DESC"
    else:
        query += " ORDER BY a.id DESC"
        
    ads = []
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        for row in cursor.fetchall():
            ads.append({
                'id': row[0], 'brand': row[1], 'model': row[2], 'year': row[3],
                'price': row[4], 'description': row[5], 'image_path': row[6], 'phone': row[7]
            })
            
    return render(request, 'cars.html', {'ads': ads, 'custom_user': get_current_user(request)})

# 4. Профиль и Добавление объявлений
def profile_view(request):
    current_user = get_current_user(request)
    if not current_user:
        return redirect('login')
        
    # Инициализируем хранилище строго внутри статики проекта
    fs = FileSystemStorage(location=BASE_DIR / 'static')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Обновление аватара
        if action == 'update_avatar' and request.FILES.get('avatar'):
            avatar = request.FILES['avatar']
            # fs.save возвращает РЕАЛЬНОЕ сохраненное имя файла на диске
            saved_name = fs.save(f"images/avatars/{avatar.name}", avatar)
            
            with connection.cursor() as cursor:
                cursor.execute('UPDATE users SET avatar_path = %s WHERE id = %s', [saved_name, current_user['id']])
            return redirect('profile')
            
        # Добавление объявления
        elif action == 'add_ad':
            brand = request.POST.get('brand')
            model = request.POST.get('model')
            year = request.POST.get('year')
            price = request.POST.get('price')
            description = request.POST.get('description')
            
            img_url = ''
            if request.FILES.get('image'):
                car_img = request.FILES['image']
                # Сохраняем и получаем актуальное имя файла для базы данных
                saved_name = fs.save(f"images/cars/{car_img.name}", car_img)
                img_url = saved_name
                
            with connection.cursor() as cursor:
                cursor.execute(
                    'INSERT INTO ads (user_id, brand, model, year, price, description, image_path, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                    [current_user['id'], brand, model, int(year), int(price), description, img_url, 'active']
                )
            messages.success(request, "Объявление успешно добавлено!")
            return redirect('profile')

    # Получаем объявления текущего пользователя
    my_ads = []
    with connection.cursor() as cursor:
        cursor.execute('SELECT id, brand, model, year, price, status, image_path FROM ads WHERE user_id = %s ORDER BY id DESC', [current_user['id']])
        for row in cursor.fetchall():
            my_ads.append({
                'id': row[0], 'brand': row[1], 'model': row[2], 'year': row[3], 'price': row[4], 'status': row[5], 'image_path': row[6]
            })
            
    return render(request, 'profile.html', {'my_ads': my_ads, 'custom_user': current_user})

# 5. Смена статуса на 'sold'
def sell_car_view(request, ad_id):
    current_user = get_current_user(request)
    if not current_user:
        return redirect('login')
        
    with connection.cursor() as cursor:
        cursor.execute('UPDATE ads SET status = %s WHERE id = %s AND user_id = %s', ['sold', ad_id, current_user['id']])
        
    messages.success(request, "Автомобиль успешно снят с продажи!")
    return redirect('profile')