import os
from cs50 import SQL
from flask import Flask, redirect, render_template, request
import random
import time
import datetime
import requests

url = 'https://www.google.co.jp/search'

app = Flask(__name__)

db = SQL("sqlite:///list.db")

menu_id = []
date_list = []
menu_list = []

def error(msg):
    return render_template("error.html", message = msg)


#flask使うときpython fileの名前はapplication.pyにしないといけないっぽい
@app.route("/")
def index():

    global menu_id
    global date_list
    global menu_list

    flag = 0

    count_dict = db.execute("select id from Menu")

    count = []

    for count_dict_each in count_dict:

        count.append(count_dict_each["id"])

    #ページを再読み込みを意識するとわかりやすい
    #毎回、日時を取得して、リストに入っている日付とことなれば更新
    
    today = datetime.datetime.now()
    year = str(today.year)
    month = str(today.month)
    day = str(today.day)
    hour = str(today.hour)
    minute = str(today.minute)
    save_day = year + month + day + hour + minute
    
    #一日たったら更新→上save_dayをdayまでにする
    #一分たったら更新→minuteまで

    if len(date_list) == 0:
        date_list.append(save_day)

    if date_list[0] != save_day:
        flag = 1
        date_list[0] = save_day

    #menu_idが空 or flag==1 なら実行する
    if len(menu_id) == 0 or flag == 1:

        menu_id = list()#リストを初期化

        #countリストからランダムに三つの数字をリストで取得
        random_list = random.sample(count, 3)

        flag = 0

        for i in random_list:
            menu_id.append(i)

    menu_list = []

    #その取得した数字のidの料理名をリストに追加

    for i in menu_id:
        
        menu = db.execute("select menu from Menu where id = ?", i)
        #表示するはずだった料理が削除されていた場合
        if len(menu) != 0:
            menu_list.append(menu[0]["menu"])

        else:
            id_list = db.execute("select id from Menu where id != ?", i)
            #削除されたメニューのidが入っている添え字を取得し、104行目で更新する。
            l = menu_id.index(i)

            id_list_shuffle = random.sample(id_list, len(id_list))

            for each_id in id_list_shuffle:

                if not each_id["id"] in menu_id:
                    re_menu = db.execute("select menu from Menu where id = ?", each_id["id"])
                    menu_list.append(re_menu[0]["menu"])
                    #menu_idもしっかり更新
                    menu_id[l] = each_id["id"]
                    #print(menu_id)

                    break

    #すべてのリストを取得
    all_list_dict = db.execute("select menu from Menu")

    all_list = []

    for each in all_list_dict:

        all_list.append(each["menu"])

    return render_template("index.html", menu_list = menu_list, all_list = all_list)

@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":

        if not request.form.get("add_menu"):
            return error("読み取れませんでした")

        add = request.form.get("add_menu")

        db.execute("insert into Menu (menu) VALUES(?)", add)

        return redirect("/")

@app.route("/delete", methods=["GET", "POST"])
def delete():

    if request.method == "POST":

        if not request.form.get("delete_menu"):
            return error("読み取れませんでした")

        delete_menu = request.form.get("delete_menu")

        all_menu_list = []

        list_menu = db.execute("select menu from Menu")

        if len(list_menu) <= 3:
            return error("削除できませんでした。リストには最低３つの料理が必要です")

        for each in list_menu:
            all_menu_list.append(each["menu"])

        if not delete_menu in all_menu_list:
            return error("存在しないメニューです。もう一度料理名を確認してください")

        db.execute("delete from Menu where menu = ?", delete_menu)

        return redirect("/")

@app.route("/search",methods=["GET", "POST"])
def search_func():
    if request.method == "POST":
        menu_item = request.form.get("item")
        #print(menu_item)
        req = req = requests.get(url, params={'q': menu_item + '作り方'})
        return req.text