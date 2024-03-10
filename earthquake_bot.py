import telebot
from telebot import types
from selenium import webdriver
import folium
import time
import os
import requests
from geopy.geocoders import Nominatim


token = 'YOUR_TOKEN'
bot = telebot.TeleBot(token)

settings = {}

def get_coordinates(city):
    geolocator = Nominatim(user_agent="my_app")
    location = geolocator.geocode(city)
    if location:
        return location.latitude, location.longitude
    else:
        return None, None

def get_last_earthquake(message):
    longitude = settings['longitude']
    latitude = settings['latitude']
    maxradius = settings['maxradius']

    url = 'https://earthquake.usgs.gov/fdsnws/event/1/query'
    params = {
        'format': 'geojson',
        'latitude': latitude,
        'longitude': longitude,
        'maxradiuskm': maxradius,
    }
    response = requests.get(url, params=params)
    json = response.json()  

    try:
        earthquake = json['features'][0]['geometry']['coordinates']
    except:
        bot.send_message(message.chat.id, "В этом радиусе давно не было землетрясений!")
        main(message)

    earthquake = json['features'][0]['geometry']['coordinates']
    map = folium.Map(location=[earthquake[1], earthquake[0]], zoom_start=9)
    folium.Marker([earthquake[1], earthquake[0]]).add_to(map)

    map.save("map.html")

    driver = webdriver.Chrome()
    current_dir = os.getcwd()
    map_file = os.path.join(current_dir, 'map.html')
    driver.get(f"file:///{map_file}")
    time.sleep(1)

    driver.save_screenshot("map.png")
    driver.quit()

    photo = open('./map.png', 'rb')

    bot.send_message(message.chat.id, f''' 
    <b>Последнее землятрясение: </b> в радиусе <i>{settings['maxradius']} км</i> от города <i>{settings['city'].capitalize()}</i>
    ''', parse_mode='html', reply_markup=types.ReplyKeyboardRemove())

    bot.send_photo(message.chat.id, photo)

    place = json['features'][0]['properties']['place']
    magnitude = json['features'][0]['properties']['mag']
    depth = earthquake[2]
    
    unix_timestamp = str(json['features'][0]['properties']['time'])[:-3]
    local_time = time.localtime(int(unix_timestamp))
    formatted_date = time.strftime("%Y-%m-%d %H:%M:%S", local_time)

    bot.send_message(message.chat.id, f'Расположение: {place}\nМагнитуда: {magnitude}\nГлубина: {depth}\nДата: {formatted_date}')

    main(message)

def edit_city(message):
    city = message.text
    latitude, longitude = get_coordinates(city)
    settings['longitude'] = longitude
    settings['latitude'] = latitude
    settings['city'] = city
    bot.send_message(message.chat.id, 'Город был обновлен!')
    main(message)

def edit_maxradius(message):
    maxradius = message.text
    settings['maxradius'] = maxradius
    bot.send_message(message.chat.id, 'Радиус был обновлен!')
    main(message)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 'Укажите город:')
    bot.register_next_step_handler(message, city_handler)

def city_handler(message):
    city = message.text
    latitude, longitude = get_coordinates(city)

    bot.send_message(message.chat.id, 'Введите радиус(км), вокруг вашего города, где могло быть зафиксировано замлятрясение: ')
    
    settings['city'] = city
    settings['longitude'] = longitude
    settings['latitude'] = latitude
    
    bot.register_next_step_handler(message, maxradius_handler)

def maxradius_handler(message):
    maxradius = message.text
    settings['maxradius'] = maxradius

    bot.send_message(message.chat.id, 'Ваши настройки были сохранены!')

    main(message)
    
def main(message):
    markup = types.ReplyKeyboardMarkup()
    btn1 = types.KeyboardButton('Посмотреть последнее ближайшее землетрясение')
    btn2 = types.KeyboardButton('Редактировать город')
    btn3 = types.KeyboardButton('Редактировать радиус')
    markup.row(btn1)
    markup.row(btn2, btn3)

    bot.send_message(message.chat.id, 'Выберите действие:', reply_markup=markup)
    bot.register_next_step_handler(message, on_click)

def on_click(message):
    if message.text == 'Посмотреть последнее ближайшее землетрясение':
        get_last_earthquake(message)
    elif message.text == 'Редактировать город':
        bot.send_message(message.chat.id, 'Введите город: ', reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, edit_city)
    elif message.text == 'Редактировать радиус':
        bot.send_message(message.chat.id, 'Введите радиус: ', reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, edit_maxradius)





bot.infinity_polling()