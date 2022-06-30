# coding: UTF-8
import datetime
import os
from os import listdir
from os.path import isfile, join
import random
import sqlite3
import sys
import threading
import time
from threading import Thread
from time import sleep

from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

import requests
from requests import get

import vk_api
from vk_api.bot_longpoll import VkBotEventType, VkBotLongPoll
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id

import lessons.lessons as lessons


class thread_stoppable(threading.Thread):
  def __init__(self, *args, **keywords):
    threading.Thread.__init__(self, *args, **keywords)
    self.killed = False

  def start(self):
    self.__run_backup = self.run
    self.run = self.__run
    threading.Thread.start(self)

  def __run(self):
    sys.settrace(self.globaltrace)
    self.__run_backup()
    self.run = self.__run_backup

  def globaltrace(self, frame, event, arg):
    if event == 'call':
      return self.localtrace
    else:
      return None

  def localtrace(self, frame, event, arg):
    if self.killed:
      if event == 'line':
        raise SystemExit()
    return self.localtrace

  def kill(self):
    self.killed = True


def update_incoming():
    try:
        global incoming, dirname, vk_upload, longpoll, vk

        while True:
            for event in longpoll.listen():
                if event.type == VkBotEventType.MESSAGE_NEW:
                    incoming.append(event)
    except:
        thread_incoming = thread_stoppable(target=update_incoming)
        thread_incoming.start()

def shuffle_dict(q):
    """
    This function is for shuffling
    the dictionary elements.
    """
    selected_keys = []
    i = 0
    while i < len(q):
        current_selection = random.choice(list(q.keys()))
        if current_selection not in selected_keys:
            selected_keys.append(current_selection)
            i = i+1
    return selected_keys

def make_keyboard_start():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('Начать урок', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('Начать тест данного урока', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('Задача на программирование', color=VkKeyboardColor.PRIMARY)
    return keyboard

def make_keyboard_final():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('Сертификат', color=VkKeyboardColor.PRIMARY)
    return keyboard

def make_keyboard_programming():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('Условие', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('Отправить решение', color=VkKeyboardColor.POSITIVE)
    return keyboard

def make_keyboard_test(answers:list):
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button(answers[0], color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button(answers[1], color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button(answers[2], color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button(answers[3], color=VkKeyboardColor.POSITIVE)
    return keyboard

def check_registration(event, vk):
    global incoming, path_members_db
    conn_members = sqlite3.connect(path_members_db)
    cursor_members = conn_members.cursor()

    sql = "SELECT * FROM members WHERE vk_id = {}".format(incoming[event].obj.from_id)
    cursor_members.execute(sql)
    sql_answer = cursor_members.fetchall()

    if len(sql_answer) == 0:
        prom = (incoming[event].obj.from_id,
                vk.users.get(user_ids=incoming[event].obj.from_id)[0]['first_name'], 1, 0, 0)
        new_user = [prom,]
        cursor_members.executemany("INSERT INTO members VALUES (?,?,?,?,?)", new_user)
        conn_members.commit()

        vk.messages.send(peer_id=incoming[event].obj.from_id, random_id=get_random_id(),
                message='вы зарегистрировались на уроки пайтона', keyboard=make_keyboard_start().get_keyboard())

    else:
        vk.messages.send(peer_id=incoming[event].obj.from_id, random_id=get_random_id(),
        message='Вы уже записаны на уроки пайтона', keyboard=make_keyboard_start().get_keyboard())


def send_lesson(vk, event):
    global incoming, path_members_db
    conn_members = sqlite3.connect(path_members_db)
    cursor_members = conn_members.cursor()

    sql = "SELECT * FROM members WHERE vk_id LIKE {}".format(incoming[event].obj.from_id)
    cursor_members.execute(sql)

    last_lesson = cursor_members.fetchall()
    last_lesson = last_lesson[0]
    last_lesson = last_lesson[2]

    full = lessons.get_full(last_lesson)

    i = 0

    while i < len(full) - 1:
      image = vk_upload.photo_messages(full[i + 1])[0]
      attachments = ['photo{}_{}'.format(image['owner_id'], image['id'])]
      answer = full[i]
      vk.messages.send(peer_id=incoming[event].obj.from_id, random_id=get_random_id(),
                       message=answer, attachment=','.join(attachments))
      i += 2

def test(vk, incoming_test_copy):
    global incoming, path_members_db, on_test
    your_id = incoming_test_copy.obj.from_id
    conn_members = sqlite3.connect(path_members_db)
    cursor_members = conn_members.cursor()

    sql = "SELECT * FROM members WHERE vk_id LIKE {}".format(incoming_test_copy.obj.from_id)
    cursor_members.execute(sql)
    last_lesson = cursor_members.fetchall()[0][2]
    full = lessons.get_test(last_lesson)

    for i in full:
        shuf = list(zip(full[i], [1, 0, 0,0]))
        random.shuffle(shuf)
        q, a = zip(*shuf)
        full[i] = [q,a]
    keys = shuffle_dict(full)


    b = 0
    total_right = 0
    total = 0

    for question in keys:
        total += 1

        keyboard = make_keyboard_test(full[question][0]).get_keyboard()
        vk.messages.send(peer_id=your_id, random_id=get_random_id(),
                message=question, keyboard=keyboard)
        start = time.time()
        flag = False

        while time.time() - start < 30:
            if flag:
                break

            elif incoming != []:
                for event in range(len(incoming)):
                    if incoming[event].obj.from_id == your_id:
                        if incoming[event].obj.text == full[question][0][full[question][1].index(1)]:
                            del incoming[event]
                            total_right += 1
                            b += 1
                            flag = True
                            break
                        else:
                             del incoming[event]
                             flag = True
                             b += 1
                             break
        else:
            vk.messages.send(peer_id=your_id, random_id=get_random_id(),
                                message='время истекло, начните заново', keyboard=make_keyboard_start().get_keyboard())
            del on_test[on_test.index(your_id)]
            return None

    del on_test[on_test.index(your_id)]

    vk.messages.send(peer_id=your_id, random_id=get_random_id(),
                                message='Итого правильных ответов: {} из {}.'.format(total_right,total,))
    if total == total_right:
        vk.messages.send(peer_id=your_id, random_id=get_random_id(),
                                message='Вы прошли', keyboard=make_keyboard_start().get_keyboard())
        sql = """
            UPDATE members
            SET test = {}
            WHERE vk_id = '{}'
            """.format(1, your_id)

        cursor_members.execute(sql)
        conn_members.commit()


        sql = "SELECT * FROM members WHERE vk_id LIKE {}".format(incoming_test_copy.obj.from_id)
        cursor_members.execute(sql)
        last = cursor_members.fetchall()[0]

        if [last[3], last[4]] == [1, 1]:
            sql = """
            UPDATE members
            SET last_lesson = {}
            WHERE vk_id = '{}'
            """.format(last[2]+1, your_id)

            cursor_members.execute(sql)
            conn_members.commit()

            if last[2] == number_of_lessons:
                    vk.messages.send(peer_id=your_id, random_id=get_random_id(),
                            message='Поздравляем, вы закончили наш курс', keyboard=make_keyboard_final().get_keyboard())
                    send_sertificate(your_id)
            else:
                vk.messages.send(peer_id=your_id, random_id=get_random_id(),
                        message='Вы перешли на следующий урок', keyboard=make_keyboard_start().get_keyboard())
                sql = """
                UPDATE members
                SET test = {}
                WHERE vk_id = '{}'
                """.format(0, your_id)

                cursor_members.execute(sql)
                conn_members.commit()

                sql = """
                UPDATE members
                SET prog = {}
                WHERE vk_id = '{}'
                """.format(0, your_id)

                cursor_members.execute(sql)
                conn_members.commit()

    else:
        vk.messages.send(peer_id=your_id, random_id=get_random_id(),
                                message='Вы не прошли тест', keyboard=make_keyboard_start().get_keyboard())




def programming_task(vk, incoming_test_copy):
    global incoming, path_members_db, on_test
    your_id = incoming_test_copy.obj.from_id
    conn_members = sqlite3.connect(path_members_db)
    cursor_members = conn_members.cursor()

    sql = "SELECT * FROM members WHERE vk_id LIKE {}".format(incoming_test_copy.obj.from_id)
    cursor_members.execute(sql)
    last_lesson = cursor_members.fetchall()[0][2]
    print('Полседний урок: ', last_lesson)

    your_id = incoming_test_copy.obj.from_id
    flag = False

    vk.messages.send(peer_id=your_id, random_id=get_random_id(),
                                message='Выберите действие:', keyboard=make_keyboard_programming().get_keyboard())

    start = time.time()
    while time.time() - start < 10:
        if flag:
            break

        elif incoming != []:
            for event in range(len(incoming)):
                if incoming[event].obj.from_id == your_id:
                    if incoming[event].obj.text.lower() == 'условие':
                        vk.messages.send(peer_id=your_id, random_id=get_random_id(),
                                message=lessons.get_programming(last_lesson),  keyboard=make_keyboard_start().get_keyboard())
                        del incoming[event]
                        flag = True
                        break

                    elif incoming[event].obj.text.lower() == 'отправить решение':
                        vk.messages.send(peer_id=your_id, random_id=get_random_id(),
                                message='Отправьте нам файлик с кодом. У вас есть 10 секунд.')
                        del incoming[event]

                        start = time.time()
                        while time.time() - start < 10:
                            if flag:
                                break

                            elif incoming != []:
                                for event in range(len(incoming)):
                                    if incoming[event].obj.from_id == your_id:
                                        print(incoming[event])
                                        answer = incoming[event].obj.attachments
                                        del incoming[event]
                                        flag = True
                                        break
                        else:
                            vk.messages.send(peer_id=your_id, random_id=get_random_id(),
                                                message='Время на отправление истекло, попробуйте позже.', keyboard=make_keyboard_start().get_keyboard())
                            del on_test[on_test.index(your_id)]
                            return None

                        with open(dirname + '/lessons/programs/prog.py'.format() , "wb") as file:
                            response = get(answer[0]['doc']['url'])
                            file.write(response.content)

                        vk.messages.send(peer_id=your_id, random_id=get_random_id(),
                                                message='**проверяем**',)

                        check = lessons.checking(your_id, last_lesson)

                        if type(check) != bool :
                            vk.messages.send(peer_id=your_id, random_id=get_random_id(),
                                                message=check,)

                        elif check==False:
                            vk.messages.send(peer_id=your_id, random_id=get_random_id(),
                                                message='Вы не прошли задачу', keyboard=make_keyboard_start().get_keyboard())
                        else:
                            vk.messages.send(peer_id=your_id, random_id=get_random_id(),
                                                message='Вы прошли задачу',  keyboard=make_keyboard_start().get_keyboard())

                            sql = """
                                UPDATE members
                                SET prog = {}
                                WHERE vk_id = '{}'
                                """.format(1, your_id)

                            cursor_members.execute(sql)
                            conn_members.commit()


                            sql = "SELECT * FROM members WHERE vk_id LIKE {}".format(incoming_test_copy.obj.from_id)
                            cursor_members.execute(sql)
                            last = cursor_members.fetchall()[0]

                            if [last[3], last[4]] == [1, 1]:
                                sql = """
                                UPDATE members
                                SET last_lesson = {}
                                WHERE vk_id = '{}'
                                """.format(last[2]+1, your_id)

                                cursor_members.execute(sql)
                                conn_members.commit()

                                if last[2] == number_of_lessons:
                                    vk.messages.send(peer_id=your_id, random_id=get_random_id(),
                                            message='Поздравляем, вы закончили наш курс', keyboard=make_keyboard_final().get_keyboard())
                                    send_sertificate(your_id)
                                else:
                                    vk.messages.send(peer_id=your_id, random_id=get_random_id(),
                                            message='Вы перешли на следующий урок', keyboard=make_keyboard_start().get_keyboard())

                                    sql = """
                                    UPDATE members
                                    SET test = {}
                                    WHERE vk_id = '{}'
                                    """.format(0, your_id)

                                    cursor_members.execute(sql)
                                    conn_members.commit()

                                    sql = """
                                    UPDATE members
                                    SET prog = {}
                                    WHERE vk_id = '{}'
                                    """.format(0, your_id)

                                    cursor_members.execute(sql)
                                    conn_members.commit()

                    else:
                        del incoming[event]
    else:
        vk.messages.send(peer_id=your_id, random_id=get_random_id(),
                            message='Время на отправление истекло, попробуйте позже.', keyboard=make_keyboard_start().get_keyboard())


def database_thread():
    global passed_test, passed_prog, registered, path_members_db, final, number_of_lessons

    while True:
        conn_members = sqlite3.connect(path_members_db)
        cursor_members = conn_members.cursor()

        sql = "SELECT * FROM members"
        cursor_members.execute(sql)
        last_lesson = cursor_members.fetchall()

        registered_prom =  []
        passed_test_prom = []
        passed_prog_prom = []
        final_prom = []

        for i in last_lesson:
            registered_prom.append(i[0])
            if i[3] == 1:
                passed_test_prom.append(i[0])
            if i[4] == 1:
                passed_prog_prom.append(i[0])
            if i[2]-1 == number_of_lessons:
                final_prom.append(i[0])

        registered = registered_prom
        passed_test = passed_test_prom
        passed_prog =  passed_prog_prom
        final = final_prom

        time.sleep(2)


#---------------------------------------------------------------------------------------------------
incoming = []
on_test = []
passed_test = []
passed_prog = []
registered = []
final = []

dirname = os.path.dirname(__file__)


onlyfiles = [f for f in listdir(dirname+'/lessons/') if not isfile(join(dirname+'/lessons/', f))][:-2]
number_of_lessons = len(onlyfiles)

path_members =  dirname + '/databases/'
path_members_db = path_members + 'members.db'

if not os.path.exists(path_members_db):
    conn_members = sqlite3.connect(path_members_db)
    cursor_members  = conn_members.cursor()
    cursor_members.execute("""CREATE TABLE members
        (vk_id integer, name text, last_lesson integer, test integer, prog integer)
        """)

else:
    conn_members = sqlite3.connect(path_members_db)
    cursor_members = conn_members.cursor()

def send_sertificate(event_id):
    # font = ImageFont.truetype(<font-file>, <font-size>)

    font = ImageFont.truetype("C:/Windows/Fonts/Arial.ttf", 80)

    img = Image.open("sertificate_template/Sertificate.png")
    draw = ImageDraw.Draw(img)
    info = vk.users.get(user_ids=event_id)[0]
    draw.text((110, 450),"{} {}".format(info['first_name'],info['last_name']),(20,20,20),font=font)

    img.save('sertificate_template/srtification_out.png')


    image = vk_upload.photo_messages(dirname + '/sertificate_template/srtification_out.png')[0]
    attachments = ['photo{}_{}'.format(image['owner_id'], image['id'])]
    answer = 'Ваш сертификат'
    vk.messages.send(peer_id=event_id, random_id=get_random_id(),
                       message=answer, attachment=','.join(attachments))

#---------------------------------------------------------------------------------------------------------

import sys
sys.path.append(dirname + '/lessons/')
vk_session = vk_api.VkApi(token='')
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, '')
vk_upload = vk_api.VkUpload(vk_session)




# import subprocess
# file = "foo.txt"
# text = "'comment'"
# output = subprocess.check_output(["BZR", "commit", file, "-m", text])
# print(output)


def main():
    global incoming, dirname, vk_upload, longpoll, vk, cursor_members, on_test
    start_button = 'начать'

    while True:

        if incoming != []:
            for event in range(len(incoming)):
                if incoming[event].obj.from_id in on_test:
                    continue

                elif incoming[event].obj.text.lower() == start_button:
                    check_registration( event, vk)
                    del incoming[event]

                elif incoming[event].obj.text.lower() == 'начать урок':

                    if (incoming[event].obj.from_id in final):
                        vk.messages.send(peer_id=incoming[event].obj.from_id, random_id=get_random_id(),
                                message='Вы уже закончили наш курс',  keyboard=make_keyboard_final().get_keyboard())
                        del incoming[event]

                    elif (incoming[event].obj.from_id in registered):
                        send_lesson(vk, event)
                        del incoming[event]

                    else:
                        vk.messages.send(peer_id=incoming[event].obj.from_id, random_id=get_random_id(),
                                message='Вы не зарегистрированы')
                        del incoming[event]

                elif incoming[event].obj.text.lower() == 'начать тест данного урока':
                    if (incoming[event].obj.from_id in final):
                        vk.messages.send(peer_id=incoming[event].obj.from_id, random_id=get_random_id(),
                                message='Вы уже закончили наш курс',  keyboard=make_keyboard_final().get_keyboard())
                        del incoming[event]

                    elif (incoming[event].obj.from_id in registered) and (incoming[event].obj.from_id not in passed_test):
                        incoming_test_copy = incoming[event]
                        on_test.append(incoming[event].obj.from_id)
                        del incoming[event]

                        thread_test = thread_stoppable(target=test, args=[vk, incoming_test_copy])
                        thread_test.run()

                    elif (incoming[event].obj.from_id in passed_test):
                        vk.messages.send(peer_id=incoming[event].obj.from_id, random_id=get_random_id(),
                                message='Вы уже прошли тест данного урока',  keyboard=make_keyboard_start().get_keyboard())
                        del incoming[event]
                    else:
                        vk.messages.send(peer_id=incoming[event].obj.from_id, random_id=get_random_id(),
                                message='Вы не зарегистрированы')
                        del incoming[event]


                elif incoming[event].obj.text.lower() == 'задача на программирование':

                    if (incoming[event].obj.from_id in final):
                        vk.messages.send(peer_id=incoming[event].obj.from_id, random_id=get_random_id(),
                                message='Вы уже закончили наш курс',  keyboard=make_keyboard_final().get_keyboard())
                        del incoming[event]

                    elif (incoming[event].obj.from_id in registered) and (incoming[event].obj.from_id not in passed_prog):
                        incoming_test_copy = incoming[event]
                        del incoming[event]
                        programming_task(vk, incoming_test_copy)

                    elif (incoming[event].obj.from_id in passed_prog):
                        vk.messages.send(peer_id=incoming[event].obj.from_id, random_id=get_random_id(),
                                message='Вы уже написали программу данного урока',  keyboard=make_keyboard_start().get_keyboard())
                        del incoming[event]
                    else:
                        vk.messages.send(peer_id=incoming[event].obj.from_id, random_id=get_random_id(),
                                message='Вы не зарегистрированы')
                        del incoming[event]

                elif (incoming[event].obj.text.lower() == 'сертификат') and (incoming[event].obj.from_id in final):
                    send_sertificate(incoming[event].obj.from_id)
                    del incoming[event]

                else:
                    if incoming[event].obj.from_id in registered:
                        vk.messages.send(peer_id=incoming[event].obj.from_id, random_id=get_random_id(),
                                message='Я не знаю такой команды',  keyboard=make_keyboard_start().get_keyboard())

                    elif (incoming[event].obj.from_id in final):
                        vk.messages.send(peer_id=incoming[event].obj.from_id, random_id=get_random_id(),
                                message='Я не знаю такой команды',  keyboard=make_keyboard_final().get_keyboard())
                        del incoming[event]

                    else:
                        vk.messages.send(peer_id=incoming[event].obj.from_id, random_id=get_random_id(),
                                message='Вы не зарегистрированы')
                    del incoming[event]


thread_incoming = thread_stoppable(target=update_incoming)
thread_incoming.start()

thread_database_thread = thread_stoppable(target=database_thread)
thread_database_thread.start()

thread_main = thread_stoppable(target=main)
thread_main.start()
