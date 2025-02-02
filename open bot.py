import telebot
from telebot import types
import sqlite3
import schedule
import time
import threading

TOKEN = '7129026099:AAF0HwpONeNA4itYTe3H1ekFg4NvA3SdH-0'
ADMIN_IDS = ['7910690122', '479147802', '5553367511', '6681528504', 'ADMIN_ID_5']
bot = telebot.TeleBot(TOKEN)

user_data = {}
mafia_active = False
user_state = {}
mafia_participants = set()
MAX_PARTICIPANTS = 15

default_description = """
🎮 **بازی مافیا**
- بازی گروهی هیجان‌انگیز
- مناسب برای 8 تا 15 نفر
- مدت زمان: حدود 1 ساعت
"""
custom_description = default_description

def init_db():
    conn = sqlite3.connect('mafia_bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, name TEXT, age INTEGER)''')
    conn.commit()
    conn.close()

def notify_admins(message):
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, message)
        except Exception as e:
            print(f"خطا در ارسال پیام به {admin_id}: {str(e)}")  # چاپ خطا در کنسول

def notify_all_users(message):
    for user_id in user_data.keys():
        bot.send_message(user_id, message)

def reset_mafia_participants():
    global mafia_participants
    mafia_participants.clear()
    notify_all_users("🔄 **تمام کاربران ثبت‌نام کرده در مافیا ریست شدند.**")

def schedule_reset():
    schedule.every().day.at("07:00").do(reset_mafia_participants)
    while True:
        schedule.run_pending()
        time.sleep(1)

# شروع تایمر در یک ترد جدید
threading.Thread(target=schedule_reset, daemon=True).start()

def get_main_markup(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if user_id in user_data:
        button_mafia = types.KeyboardButton("🃏 مافیا")
        markup.add(button_mafia)
    if str(user_id) in ADMIN_IDS:
        button_admin = types.KeyboardButton("👑 پنل مدیریت")
        markup.add(button_admin)
    return markup

def get_admin_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_activate_mafia = types.KeyboardButton("فعال کردن مافیا")
    button_deactivate_mafia = types.KeyboardButton("غیرفعال کردن مافیا")
    button_edit_description = types.KeyboardButton("ویرایش توضیحات")
    button_reset_description = types.KeyboardButton("بازنشانی توضیحات")
    button_participants = types.KeyboardButton("تعداد شرکت‌کنندگان")
    button_set_max_participants = types.KeyboardButton("تنظیم حداکثر شرکت‌کنندگان")
    button_reset_now = types.KeyboardButton("ریست کاربران مافیا")
    button_back = types.KeyboardButton("🔙 بازگشت به منوی اصلی")
    markup.add(button_activate_mafia, button_deactivate_mafia)
    markup.add(button_edit_description, button_reset_description)
    markup.add(button_participants, button_set_max_participants)
    markup.add(button_reset_now, button_back)
    return markup

def get_mafia_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_join = types.KeyboardButton("شرکت در مافیا")
    button_leave = types.KeyboardButton("لغو شرکت در مافیا")
    button_info = types.KeyboardButton("توضیحات بازی")
    button_back = types.KeyboardButton("🔙 بازگشت به منوی اصلی")
    markup.add(button_join, button_leave)
    markup.add(button_info)
    markup.add(button_back)
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id not in user_data:
        user_state[user_id] = 'waiting_for_name'
        bot.send_message(message.chat.id, 
                        "🎉 **به ربات مافیا خوش آمدید!**\nلطفاً نام خود را وارد کنید:")
    else:
        user_state[user_id] = 'main_menu'
        bot.send_message(message.chat.id, 
                        "به ربات مافیا خوش آمدید!", 
                        reply_markup=get_main_markup(user_id))

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    global mafia_active, custom_description, MAX_PARTICIPANTS
    user_id = message.from_user.id
    username = message.from_user.username  # دریافت یوزر نیم

    try:
        # بررسی حالت انتظار برای نام
        if user_state.get(user_id) == 'waiting_for_name':
            name = message.text
            user_data[user_id] = {'name': name, 'age': None}  # سن اولیه به None تنظیم می‌شود
            user_state[user_id] = 'waiting_for_age'  # تغییر حالت به انتظار برای سن
            bot.send_message(message.chat.id, "لطفاً سن خود را وارد کنید:")
            return

        if user_state.get(user_id) == 'waiting_for_age':
            try:
                age = int(message.text)
                user_data[user_id]['age'] = age  # سن کاربر ذخیره می‌شود
                user_state[user_id] = 'main_menu'

                # ارسال اطلاعات به ادمن
                admins_message = (f"👤 نام: {user_data[user_id]['name']}\n"
                                  f"🆔 یوزر نیم: @{username}\n"
                                  f"🌟 سن: {age}\n")
                print(f"ارسال اطلاعات به مدیران: {admins_message}")  # چاپ اطلاعات برای دیباگ
                notify_admins(admins_message)

                # ارسال عکس پروفایل کاربر
                profile_photo = bot.get_user_profile_photos(user_id, limit=1)
                if profile_photo.total_count > 0:
                    photo = profile_photo.photos[0][-1].file_id  # آخرین عکس پروفایل
                    for admin_id in ADMIN_IDS:
                        try:
                            bot.send_photo(admin_id, photo, caption=admins_message)  # ارسال به مدیران
                        except Exception as e:
                            print(f"خطا در ارسال عکس به {admin_id}: {str(e)}")  # چاپ خطا در کنسول
                            print(f"مشخصات: admin_id={admin_id}, photo={photo}")  # چاپ مشخصات برای دیباگ
                else:
                    # ارسال اطلاعات به ادمن بدون عکس
                    notify_admins(admins_message)

                bot.send_message(message.chat.id, f"ثبت نام شما با موفقیت انجام شد، {user_data[user_id]['name']} عزیز!\nشما باارسال مجدد /start می‌توانید به منوی مافیا بروید.")
                return
            except ValueError:
                bot.send_message(message.chat.id, "لطفاً یک عدد معتبر برای سن وارد کنید.")
                return

        if message.text == "🔙 بازگشت به منوی اصلی":
            user_state[user_id] = 'main_menu'
            bot.send_message(message.chat.id, "به منوی اصلی بازگشتید:", 
                            reply_markup=get_main_markup(user_id))
            return

        if message.text == "👑 پنل مدیریت":
            if str(user_id) in ADMIN_IDS:
                user_state[user_id] = 'admin'
                bot.send_message(message.chat.id, "پنل مدیریت:", reply_markup=get_admin_markup())
            return

        if message.text == "🃏 مافیا":
            user_state[user_id] = 'mafia'
            bot.send_message(message.chat.id, "منوی مافیا:", reply_markup=get_mafia_markup())
            return

        if message.text == "فعال کردن مافیا":
            if str(user_id) in ADMIN_IDS:
                mafia_active = True
                bot.send_message(message.chat.id, "✅ **بازی مافیا فعال شد.**")
                notify_all_users("🎉 **بازی مافیا فعال شد!**")
            return

        if message.text == "غیرفعال کردن مافیا":
            if str(user_id) in ADMIN_IDS:
                mafia_active = False
                mafia_participants.clear()
                bot.send_message(message.chat.id, "❌ **بازی مافیا غیرفعال شد.**")
                notify_all_users("❌ **بازی مافیا غیرفعال شد!**")
            return

        if message.text == "شرکت در مافیا":
            if not mafia_active:
                bot.send_message(message.chat.id, "⚠️ **مافیا در حال حاضر فعال نیست.**")
                return
            if len(mafia_participants) >= MAX_PARTICIPANTS:
                bot.send_message(message.chat.id, "⚠️ **متاسفانه ظرفیت تکمیل است.**")
                return
            if user_id in mafia_participants:
                bot.send_message(message.chat.id, "📌 **شما قبلاً ثبت‌نام کرده‌اید.**")
                return
            mafia_participants.add(user_id)
            bot.send_message(message.chat.id, f"🎉 **شما در مافیا ثبت‌نام شدید.** تعداد فعلی: {len(mafia_participants)}/{MAX_PARTICIPANTS}")
            notify_admins(f"{user_data[user_id]['name']} در مافیا ثبت‌نام کرد.")
            return

        if message.text == "لغو شرکت در مافیا":
            if user_id in mafia_participants:
                mafia_participants.remove(user_id)
                bot.send_message(message.chat.id, "❌ **شرکت شما در مافیا لغو شد.**")
                notify_admins(f"{user_data[user_id]['name']} شرکت خود را در مافیا لغو کرد.")
            else:
                bot.send_message(message.chat.id, "⚠️ **شما در مافیا ثبت‌نام نکرده‌اید.**")
            return

        if message.text == "توضیحات بازی":
            bot.send_message(message.chat.id, custom_description)
            return

        if message.text == "تعداد شرکت‌کنندگان":
            participants_list = "\n".join(
                [f"{i + 1}. {user_data[user_id]['name']}" 
                 for i, user_id in enumerate(mafia_participants)]
            )
            bot.send_message(message.chat.id, f"👥 **تعداد فعلی: {len(mafia_participants)}/{MAX_PARTICIPANTS}**\n\n**شرکت‌کنندگان:**\n{participants_list}")
            return

        if message.text == "تنظیم حداکثر شرکت‌کنندگان":
            user_state[user_id] = 'waiting_for_max_participants'
            bot.send_message(message.chat.id, "لطفاً حداکثر تعداد شرکت‌کنندگان را وارد کنید:")
            return

        if user_state.get(user_id) == 'waiting_for_max_participants':
            try:
                new_max = int(message.text)
                if new_max < 8:
                    bot.send_message(message.chat.id, "حداقل تعداد شرکت‌کنندگان 8 نفر است.")
                    return
                MAX_PARTICIPANTS = new_max
                bot.send_message(message.chat.id, f"✅ **حداکثر تعداد شرکت‌کنندگان به {new_max} تغییر یافت.**")
            except ValueError:
                bot.send_message(message.chat.id, "لطفاً یک عدد معتبر وارد کنید.")
                return

        if str(user_id) in ADMIN_IDS:
            if message.text == "ویرایش توضیحات":
                user_state[user_id] = 'waiting_for_description'
                bot.send_message(message.chat.id, "لطفاً توضیحات جدید را وارد کنید:")
                return

            if message.text == "بازنشانی توضیحات":
                custom_description = default_description
                bot.send_message(message.chat.id, "✅ **توضیحات به حالت پیش‌فرض بازگشت.**")
                notify_all_users("🔄 **توضیحات بازی به حالت پیش‌فرض بازگشت.**")
                return

            if message.text == "ریست کاربران مافیا":
                reset_mafia_participants()
                bot.send_message(message.chat.id, "✅ **تمام کاربران ثبت‌نام کرده در مافیا ریست شدند.**")
                return

            if user_state.get(user_id) == 'waiting_for_description':
                custom_description = message.text
                user_state[user_id] = 'admin'
                bot.send_message(message.chat.id, "✅ **توضیحات با موفقیت به‌روزرسانی شد.**")
                notify_all_users("🔄 **توضیحات بازی به‌روزرسانی شد.**")
                return

    except Exception as e:
        bot.send_message(message.chat.id, "خطایی پیش آمد، لطفاً دوباره امتحان کنید.")
        print(f"خطا: {str(e)}")  # چاپ خطا در کنسول

init_db()

if __name__ == "__main__":
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"خطا: {str(e)}")