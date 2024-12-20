import os
from random import choice

from datetime import date
import logging
from logging.handlers import RotatingFileHandler
import django
from django.utils.timezone import now
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, \
    LabeledPrice, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, \
      CallbackContext, CallbackQueryHandler, PreCheckoutQueryHandler

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'python_meetup.settings')
django.setup()

logger = logging.getLogger("Bot logger")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler("app.log", maxBytes=200)
logger.addHandler(handler)

from python_meetup.settings import TG_BOT_TOKEN, PAY_MASTER_TOKEN

from bot.models import User, Questions, Donate, Program, Application


def start(update: Updater, context: CallbackContext):
    logger.info("Начало работы")
    keyboard = [
        [InlineKeyboardButton("Начать лекцию",
                              callback_data="start_lecture"),
         InlineKeyboardButton('Закончить лекцию',
                              callback_data="end_lecture")] if context.bot_data["user"].status == "SPEAKER" else [],
        [InlineKeyboardButton('Вопросы ко мне',
                              callback_data="my_questions")] if context.bot_data["user"].status == "SPEAKER" else [],
        [InlineKeyboardButton("Программа",
                              callback_data="show_program"),
         InlineKeyboardButton("Задать вопрос спикеру",
                              callback_data="add_question")],
        [InlineKeyboardButton("Хочу познакомиться",
                              callback_data="networking"),
         InlineKeyboardButton("Задонатить",
                              callback_data="make_donation")],
        [InlineKeyboardButton("Подать заявку на участие",
                              callback_data="make_application")],
        [InlineKeyboardButton("Подписаться на рассылку",
                              callback_data="get_notifications")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        update.message.reply_text(
            "Добро пожаловать на наше мероприятие",
            reply_markup=reply_markup,
        )
        message = update.effective_message
        context.bot.delete_message(
            chat_id=message.chat_id,
            message_id=update.message.message_id
        )
    elif update.callback_query:
        query = update.callback_query
        query.message.reply_text(
            "Выберите действие:",
            reply_markup=reply_markup,
        )
        context.bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id
        )

    return "CHOOSE_ACTION"


def choose_action(update: Updater, context: CallbackContext):
    logger.info("Выбор действия")
    data = update.callback_query.data
    if data == "start_lecture":
        return start_lecture(update, context)
    elif data == "end_lecture":
        return end_lecture(update, context)
    elif data == "my_questions":
        return get_questions(update, context)
    elif data == "show_program":
        return show_program(update, context)
    elif data == "add_question":
        return add_question(update, context)
    elif data == "networking":
        return get_networking(update, context)
    elif data == "make_donation":
        return get_donation(update, context)
    elif data == "make_application":
        return make_application(update, context)
    elif data == "get_notifications":
        return get_notifications(update, context)


def start_lecture(update: Updater, context: CallbackContext):
    logger.info("Начало доклада")
    context.bot_data["user"].ready_to_questions = True
    context.bot_data["user"].save
    return start(update, context)


def end_lecture(update: Updater, context: CallbackContext):
    logger.info("Конец доклада")
    context.bot_data["user"].ready_to_questions = False
    context.bot_data["user"].save
    return start(update, context)


def get_questions(update: Updater, context: CallbackContext):
    logger.info("Получить вопрос от слушателя")
    user = context.bot_data["user"]

    questions = Questions.objects.filter(answerer=user)
    keyboard = [
        [InlineKeyboardButton("Главное меню", callback_data="to_start")],
    ]
    text = ""
    for question in questions:
        text += f"Вопрос от @<i><b>{question.asker.tg_nick}</b></i>: {question.text}\n\n"

    context.bot.send_message(
        chat_id=user.tg_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
        )
    message = update.effective_message
    context.bot.delete_message(
        chat_id=message.chat_id,
        message_id=message.message_id
    )
    return "HANDLE_START"


def handle_start(update: Updater, context: CallbackContext):
    logger.info("Возврат в меню")
    data = update.callback_query.data
    if data == "to_start":
        return start(update, context)


def show_program(update: Updater, context: CallbackContext):
    logger.info("Показать программу")
    today = date.today()
    program_today = (
        Program.objects.filter(date=today).prefetch_related("lectures").first()
    )

    if not program_today:
        update.callback_query.message.reply_text(
            "На сегодня программ не запланировано."
        )
        return start(update, context)

    text = "Программа на сегодня:\n\n"
    text += f"<b><i>{program_today.name}</i></b>\n\n"
    for lecture in program_today.lectures.all():
        text += f" <i>{lecture.speaker.name} - {lecture.name}</i> (с {lecture.start_time:%H:%M} \
            до {lecture.end_time:%H:%M})\n {lecture.description}\n ━━━━━━━━━━━━ \n\n"

    update.callback_query.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Главное меню", callback_data="to_start")]]
        ),
        parse_mode=ParseMode.HTML,
    )

    return "HANDLE_START"


def add_question(update: Updater, context: CallbackContext):
    logger.info("Задать вопрос докладчику")
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Введите ваш вопрос"
    )
    message = update.effective_message
    context.bot.delete_message(
        chat_id=message.chat_id,
        message_id=message.message_id
    )

    return "WAITING_QUESTION"


def waiting_question(update: Updater, context: CallbackContext):
    logger.info("Ожидание вопроса")
    question_text = update.message.text
    asker = context.bot_data["user"]
    answerer = User.objects.filter(ready_to_questions=True).first()
    if not answerer:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="К сожалению сейчас некому задать вопрос.\nДождитесь следующего спикера"
        )
        return start(update, context)
    new_question = Questions.objects.create(
        asker=asker,
        answerer=answerer,
        text=question_text
        )
    new_question.save()
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Ваш вопрос успешно отправлен"
    )
    return start(update, context)


def get_networking(update: Updater, context: CallbackContext):
    logger.info("Начать знакомиться")
    if context.bot_data["user"].active == False:
        keyboard = [
            [InlineKeyboardButton("Подтвердить участие",
                                  callback_data="confirm")],
            [InlineKeyboardButton("Главное меню",
                                  callback_data="to_start")]
        ]
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='''Вы можете пообщаться с другими участниками! Для этого\n
            нужно заполнить анкету и я подберу вам собеседника.\n
            Подтвердите участие.''',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return "CONFIRM_NETWORKING"
    if not context.bot_data["user"].name:
        return get_user_info(update, context)
    return make_networking(update, context)


def confirm_networking(update: Updater, context: CallbackContext):
    logger.info("Подтверждение знакомства")
    if update.callback_query.data == "to_start":
        return start(update, context)
    elif update.callback_query.data == "confirm":
        context.bot_data["user"].active = True
        context.bot_data["user"].save(update_fields=["active"])
        return get_networking(update, context)


def get_user_info(update: Updater, context: CallbackContext):
    logger.info("Получить информацию о пользователе")
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Введите ваше имя"
    )
    message = update.effective_message
    context.bot.delete_message(
        chat_id=message.chat_id,
        message_id=message.message_id
    )
    return "GET_NAME"


def get_name(update: Updater, context: CallbackContext):
    logger.info("Получить имя пользователя")
    message_text = update.message.text
    context.bot_data["user"].name = message_text
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Введите название вашей компании"
    )
    message = update.effective_message
    context.bot.delete_message(
        chat_id=message.chat_id,
        message_id=message.message_id
    )
    return "GET_COMPANY"


def get_company(update: Updater, context: CallbackContext):
    logger.info("Получить название компании")
    message_text = update.message.text
    context.bot_data["user"].company = message_text
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Введите вашу должность"
    )
    message = update.effective_message
    context.bot.delete_message(
        chat_id=message.chat_id,
        message_id=message.message_id
    )
    return "GET_POSITION"


def get_position(update: Updater, context: CallbackContext):
    logger.info("Получить должность пользователя")
    message_text = update.message.text
    context.bot_data["user"].position = message_text
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Сейчас я подберу вам собеседника"
    )
    message = update.effective_message
    context.bot.delete_message(
        chat_id=message.chat_id,
        message_id=message.message_id
    )
    return make_networking(update, context)


def make_networking(update: Updater, context: CallbackContext):
    logger.info("Начало нетворкинга")
    active_users_count = User.objects.filter(active=True).count()
    if active_users_count <= 1:
        text = f'<i><b>{context.bot_data["user"].name}</b></i>, рады видеть вас в нетворкинге.\n\n'
        text += 'Сейчас нет других собеседников. Я уведомлю вас, когда они появятся 🤗'

        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Главное меню", callback_data="to_start")]]
                ),
            parse_mode=ParseMode.HTML,
            )
   
        return "HANDLE_START"

    keyboard = [
        [InlineKeyboardButton("Познакомиться",
                              callback_data="find_contact")] if active_users_count > 1 else [],
        [InlineKeyboardButton("Отказаться от участия",
                              callback_data="cancel_networking")],
        [InlineKeyboardButton("Главное меню",
                              callback_data="to_start")]
    ]
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f'''
        {context.bot_data['user'].name}, рады видеть вас в нетворкинге.
        Сейчас нас {active_users_count} человек''',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return "NETWORK_COMMUNICATE"


def network_communicate(update: Updater, context: CallbackContext):
    logger.info("Возврат в главное меню/Отказаться от участия/Познакомиться")
    data = update.callback_query.data
    if data == "to_start":
        return start(update, context)
    elif data == "cancel_networking":
        return cancel_networking(update, context)
    elif data == "find_contact":
        return find_contact(update, context)


def cancel_networking(update: Updater, context: CallbackContext):
    logger.info("Отменить знакомство")
    context.bot_data["user"].active = False
    context.bot_data["user"].save
    return start(update, context)


def find_contact(update: Updater, context: CallbackContext):
    logger.info("Найти пользователя для знакомства")
    context.bot_data["networking"] = context.bot_data["user"]
    while context.bot_data["networking"] == context.bot_data["user"]:
        context.bot_data["networking"] = choice(
            User.objects.filter(active=True).exclude(
                tg_id=update.effective_chat.id
                )
        )

    keyboard = [
        [InlineKeyboardButton("Следующий контакт", callback_data="next_contact")],
        [InlineKeyboardButton("Отказаться от участия",
                              callback_data="cancel_networking")],
        [InlineKeyboardButton("Главное меню", callback_data="to_start")]
    ]
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f'''
        {context.bot_data['networking'].name}
        {context.bot_data['networking'].position} в {context.bot_data['networking'].company}
        Связаться в Telegram:
        @{context.bot_data['networking'].tg_nick}
        ''',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    message = update.effective_message
    context.bot.delete_message(
        chat_id=message.chat_id,
        message_id=message.message_id
    )
    return "NEXT_CONTACT"


def next_contact(update: Updater, context: CallbackContext):
    logger.info("Переключение кнопок")
    data = update.callback_query.data
    if data == "to_start":
        return start(update, context)
    elif data == "cancel_networking":
        return cancel_networking(update, context)
    elif data == "next_contact":
        return find_contact(update, context)

# !Донанты------------------------------------------------------------------------------------------


def get_donation(update: Updater, context: CallbackContext):
    logger.info("Обработка донатов")
    keyboard = [
        [InlineKeyboardButton("50 ₽", callback_data="donate_50")],
        [InlineKeyboardButton("100 ₽", callback_data="donate_100")],
        [InlineKeyboardButton("500 ₽", callback_data="donate_500")],
        [InlineKeyboardButton("Ввести свою сумму", callback_data="user_donate")],
        [InlineKeyboardButton("Главное меню", callback_data="to_start")],
    ]
    query = update.callback_query
    query.edit_message_text(
        text="Вы можете помочь нам финансово. Выберите сумму доната:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return "CONFIRM_DONATION"


def confirm_donation(update: Updater, context: CallbackContext):
    logger.info("Подтверждение доната")
    query = update.callback_query
    data = query.data
    chat_id = query.message.chat_id

    if update.callback_query.data == "to_start":
        return start(update, context)
    if update.callback_query.data == "user_donate":
        return user_sum_for_donate(update, context)

    if data.startswith("donate_"):
        amount = int(data.split("_")[1])
        prices = [LabeledPrice(label=f"Донат на сумму {amount} ₽",
                               amount=amount * 100)]

        context.bot.send_invoice(
            chat_id=chat_id,
            title="Донат на поддержку",
            description=f"Спасибо за ваше желание поддержать наш проект на {amount} ₽!",
            payload=f"donation_{amount}",
            provider_token=PAY_MASTER_TOKEN,
            currency="RUB",
            prices=prices,
            start_parameter="donation",
        )
        return "CHOOSE_ACTION"

    if data == "to_start":
        return start(update, context)


def user_sum_for_donate(update: Updater, context: CallbackContext):
    logger.info("Введённая пользоветелем сумма для доната")
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Введите желаемую сумму пожертования"
    )
    
    return "CONFIRM_DONATION_CUSTOM"


def confirm_donation_custom(update: Updater, context: CallbackContext):
    logger.info("Обработка суммы доната пользователя")
    chat_id = update.effective_chat.id
    message_text = update.message.text

    amount = int(message_text)
    prices = [LabeledPrice(label=f"Донат на сумму {amount} ₽", amount=amount * 100)]

    context.bot.send_invoice(
        chat_id,
        title="Донат на поддержку",
        description=f"Спасибо за ваше желание поддержать наш проект на {amount} ₽!",
        payload=f"donation_{amount}",
        provider_token=PAY_MASTER_TOKEN,
        currency="RUB",
        prices=prices,
        start_parameter="donation",
        )
    return "CHOOSE_ACTION"


def pre_checkout_callback(update: Updater, context: CallbackContext):
    logger.info("Подтверждение оплаты")
    query = update.pre_checkout_query
    payload = query.invoice_payload
    amount = int(payload.split("_")[1])

    if query.invoice_payload.startswith("donation_"):
        query.answer(ok=True)
        user, _ = User.objects.get_or_create(
            tg_id=update.effective_user.id,
            defaults={"tg_nick": update.effective_user.first_name}
        )
        Donate.objects.create(user=user, amount=amount, donated_at=now())
    else:
        query.answer(ok=False, error_message="Некорректный payload. Попробуйте снова.")


def successful_payment_callback(update: Updater, context: CallbackContext):
    logger.info("Оплата успешно принята")
    payment = update.message.successful_payment
    amount = payment.total_amount / 100

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Спасибо за ваш донат на сумму {amount} ₽!"
    )

    return start(update, context)

# !Донанты------------------------------------------------------------------------------------------


def make_application(update: Updater, context: CallbackContext):
    logger.info("Заявка на участие докладчиком")
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='''Если вы хотите принять участие в качестве спикера на\n
        следующем мероприятии, напишите тему вашего доклада'''
        )

    return "WAITING_APPLICATION"


def waiting_application(update: Updater, context: CallbackContext):
    logger.info("Сохранение темы доклада в бд")
    message = update.message.text
    applicant = context.bot_data["user"]
    new_application = Application.objects.create(
        applicant=applicant,
        message=message
        )
    new_application.save()
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Ваша заявка успешно отправлена"
    )

    return start(update, context)


def get_notifications(update: Updater, context: CallbackContext):
    logger.info("Получение рассылки")
    if context.bot_data["user"].get_notifications == True:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Вы уже подписаны на рассылку!"
        )
        return start(update, context)
    context.bot_data["user"].get_notifications = True
    context.bot_data["user"].save
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Вы подписались на нашу рассылку! Мы уведомим вас о датах следующих мероприятий!"
    )
    
    return start(update, context)


def handle_users_reply(update,
                       context,
                       ):
    logger.info("Обработка ответов пользователей")
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
        username = update.message.from_user.username
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
        username = update.callback_query.from_user.username
    else:
        return
    user, created = User.objects.get_or_create(tg_id=chat_id,
                                               defaults={'tg_state': 'START',
                                                         'tg_nick': username})
    context.bot_data['user'] = user
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = context.bot_data['user'].tg_state
    states_functions = {
        'START': start,
        'CHOOSE_ACTION': choose_action,
        'CONFIRM_NETWORKING': confirm_networking,
        'GET_NAME': get_name,
        'GET_COMPANY': get_company,
        'GET_POSITION': get_position,
        'NETWORK_COMMUNICATE': network_communicate,
        'NEXT_CONTACT': next_contact,
        'CONFIRM_DONATION': confirm_donation,
        "CONFIRM_DONATION_CUSTOM": confirm_donation_custom,
        "HANDLE_START": handle_start,
        "WAITING_QUESTION": waiting_question,
        "WAITING_APPLICATION": waiting_application,
        }
    state_handler = states_functions[user_state]
    try:
        next_state = state_handler(update, context)
        context.bot_data['user'].tg_state = next_state
        context.bot_data['user'].save()
    except Exception as err:
        print(err)


def main() -> None:
    updater = Updater(TG_BOT_TOKEN)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(PreCheckoutQueryHandler(pre_checkout_callback))
    dispatcher.add_handler(MessageHandler(Filters.successful_payment,
                                          successful_payment_callback))
    dispatcher.add_handler(
        CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(
        MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(
        CommandHandler('start', handle_users_reply))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
