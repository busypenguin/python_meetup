# Сервис PythonMeetup

Проект создан для поддержки проведения мероприятий PythonMeetup.
Бот даёт возможность слушателям доклада задать вопрос докладчику прямо в боте и познакомиться с другими разработчиками, пришедшими на встречу. Докладчики, в свою очередь, могут получать вопросы и отвечать на них прямо на сцене. Организаторы мероприятия получают власть над порядком выступлений докладчиков. Также есть возможность "поддержать" понравившегося докладчика финансово. 

### Запуск

Для запуска сайта вам понадобится Python третьей версии.

Скачайте код с GitHub. Установите зависимости:

```sh
pip install -r requirements.txt
```

Создайте базу данных:

```sh
python3 manage.py migrate
```

Запустите разработческий сервер:

```sh
python3 manage.py runserver
```

Для запуска бота используется команда `tg_bot.py`. Введите в терминал:

```sh
python3 tg_bot.py 
```

### Переменные окружения

Часть настроек проекта берётся из переменных окружения. Чтобы их определить, создайте файл `.env` в корне проекта и запишите туда данные в таком формате: `ПЕРЕМЕННАЯ=значение`.


SECRET_KEY - секретный ключ проекта
TG_BOT_TOKEN - токен тг бота
PAY_MASTER_TOKEN - токен для оплаты

Например:

```TELEGRAM_BOT_TOKEN = 087979801:A976578AqqKhDexAHU56781Hpaf3u879kijguPBKA```


## Пример