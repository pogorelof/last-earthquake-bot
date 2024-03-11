import telebot
from telebot import types
import logging
from datetime import datetime
import time
import requests
from geopy.geocoders import Nominatim
import os
from dotenv import load_dotenv
load_dotenv()


token = os.environ.get('TG_BOT_TOKEN')
google_maps_api_key = os.environ.get('GOOGLE_MAPS_KEY')

bot = telebot.TeleBot(token)
logging.basicConfig(filename='bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#State dict
settings = {
    'city': None,
    'longitude': None,
    'latitude': None,
    'maxradius': None
}

#Bot entry point
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

    if maxradius.isdigit():
        settings['maxradius'] = maxradius
        bot.send_message(message.chat.id, 'Ваши настройки были сохранены!')
        main(message)
    else:
        bot.send_message(message.chat.id, 'Нужно ввести число')
        bot.register_next_step_handler(message, maxradius_handler)
    
    
#Button rendering
def main(message):
    markup = types.ReplyKeyboardMarkup()
    btn1 = types.KeyboardButton('Посмотреть последнее ближайшее землетрясение')
    btn2 = types.KeyboardButton('Редактировать город')
    btn3 = types.KeyboardButton('Редактировать радиус')
    markup.row(btn1)
    markup.row(btn2, btn3)

    bot.send_message(message.chat.id, 'Выберите действие:', reply_markup=markup)
    bot.register_next_step_handler(message, on_click)

#Click handler
def on_click(message):
    if message.text == 'Посмотреть последнее ближайшее землетрясение':
        get_last_earthquake(message)
    elif message.text == 'Редактировать город':
        bot.send_message(message.chat.id, 'Введите город: ', reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, edit_city)
    elif message.text == 'Редактировать радиус':
        bot.send_message(message.chat.id, 'Введите радиус: ', reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, edit_maxradius)
    else:
        main(message)

#Return coordinates of city
def get_coordinates(city):
    geolocator = Nominatim(user_agent="my_app")
    location = geolocator.geocode(city)
    if location:
        return location.latitude, location.longitude
    else:
        return None, None

#Sends a photo of map with epicenter of earthquake
#and information about it
def get_last_earthquake(message):
    #Log file entry
    log_message = f"User: {message.from_user.username}\tCity: {settings['city']}\tRadius: {settings['maxradius']}"
    logging.info(log_message)
    
    url = 'https://earthquake.usgs.gov/fdsnws/event/1/query'
    params = {
        'format': 'geojson',
        'latitude': settings['latitude'],
        'longitude': settings['longitude'],
        'maxradiuskm': settings['maxradius'],
    }
    response = requests.get(url, params=params)
    json = response.json()  

    try:
        earthquake = json['features'][0]['geometry']['coordinates']
    except:
        bot.send_message(message.chat.id, "В этом радиусе давно не было землетрясений!")
        main(message)

    earthquake = json['features'][0]['geometry']['coordinates']

    map_center = f"{earthquake[1]},{earthquake[0]}"
    map_zoom = 9
    map_size = "800x600"
    map_markers = f"markers=color:red%7C{earthquake[1]},{earthquake[0]}"
    map_url = f"https://maps.googleapis.com/maps/api/staticmap?center={map_center}&zoom={map_zoom}&size={map_size}&{map_markers}&key={google_maps_api_key}"

    response = requests.get(map_url)
    with open('map.png', 'wb') as file:
        file.write(response.content)

    photo = open('./map.png', 'rb')

    bot.send_message(message.chat.id, f''' 
    <b>Последнее землятрясение: </b>в радиусе <i>{settings['maxradius']} км</i> от города <i>{settings['city'].capitalize()}</i>
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


bot.infinity_polling()