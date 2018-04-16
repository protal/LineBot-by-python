#!/usr/bin/env python
# -*- coding: utf-8 -*- 
import config
from flask import Flask,redirect,url_for,flash, request, abort, render_template , jsonify
from flask.ext.mysql import MySQL

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

# xml
from zeep import Client
from lxml import etree



app = Flask(__name__)
app.secret_key = 'protal'

line_bot_api = LineBotApi(config.line['api'])
handler = WebhookHandler(config.line['handler'])


 
# MySQL configurations
app.config['MYSQL_DATABASE_USER'] = config.db['user']
app.config['MYSQL_DATABASE_PASSWORD'] = config.db['password']
app.config['MYSQL_DATABASE_DB'] = config.db['db']
app.config['MYSQL_DATABASE_HOST'] = config.db['host']
mysql = MySQL(app)


@app.route("/")
def hello():
    return "Hello World!"

# manage 
@app.route("/manage")
def manage():
    conn = mysql.connect()
    cur = conn.cursor()
    cur.execute('SELECT * FROM Message')
    result = cur.fetchall()
    conn.close()
    return render_template('manage/index.html',Messages=result)

@app.route("/manage/message/<id>")
def getMessage(id):
    conn = mysql.connect()
    cur = conn.cursor()
    cur.execute('SELECT * FROM Message where id = '+id)
    result = cur.fetchone()
    conn.close()
    return jsonify(result)


@app.route("/manage/message/<id>/delete")
def DeleteMessage(id):
    conn = mysql.connect()
    cur = conn.cursor()
    cur.execute('''DELETE FROM Message WHERE id=%s''',id)
    conn.commit()
    conn.close()
    flash(u'Delete message success', 'success')
    return redirect(url_for('manage'))

@app.route('/manage/save', methods=['POST'])
def saveMessage():
    conn = mysql.connect()
    cur = conn.cursor()
    message = request.form['message']
    reply = request.form['reply']
    if request.form['message-id'] == "":
        cur.execute('''INSERT INTO Message (message, reply, created_at,updated_at)VALUES (%s,%s, now(),now())''',(message,reply))
        conn.commit()
        conn.close()
        flash(u'save new message success', 'success')
        return redirect(url_for('manage'))
    else :
        id = request.form['message-id']
        cur.execute('''UPDATE Message SET message = %s, reply = %s WHERE id=%s''', (message, reply,id))
        conn.commit()
        conn.close()
        flash(u'Edit message success', 'success')
        return redirect(url_for('manage'))
        


    


# - manage


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


def reply(message):
    conn = mysql.connect()
    cur = conn.cursor()
    cur.execute(
        '''SELECT * FROM Message where message = %s ORDER BY rand() LIMIT 1''', (message))
    result = cur.fetchone()
    conn.close()
    if result is None:
        return None
    else:
        return result[2]

def saveReply(message,reply,userID):
    print(userID["userId"])
    profile = line_bot_api.get_profile(userID)
    saveName = profile.user_id+"||"+profile.display_name
    conn = mysql.connect()
    cur = conn.cursor()
    cur.execute('''INSERT INTO Message (message, reply,created_by, created_at,updated_at)VALUES (%s,%s, now(),now())''',
                (message, reply, saveName))
    conn.commit()
    conn.close()


def getOilPrice():
    sendMessage = "น้องซอฟไปหาข้อมูลราคาน้ำมันจากเว็บ ptt ให้เเล้วน้าาา \n"
    client = Client('http://www.pttplc.com/webservice/pttinfo.asmx?WSDL')
    result = client.service.CurrentOilPrice("en")

    root = etree.fromstring(result)

    for r in root.xpath('DataAccess'):
        product = r.xpath('PRODUCT/text()')[0]
        price = r.xpath('PRICE/text()') or [0]
        sendMessage = sendMessage+product+' '+str(float(price[0]))+' BAHT\n'
    return sendMessage

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    if event.message.text == unicode('เช็คราคาน้ำมัน', 'utf-8'): 
        sendMessage = unicode(getOilPrice(), 'utf-8')
    elif "==" in event.message.text:
        text = event.message.text.split("==")
        message = text[0]
        replymessage = text[1]
        saveReply(message, replymessage, event.source)
        sendMessage = unicode('ขอบคุณครับที่ช่วยสอนน้องซอฟ', 'utf-8')
    else : 
        replymessage = reply(event.message.text)
        if replymessage != None:
            sendMessage = replymessage
        else :
            sendMessage = unicode('น้องซอฟไม่เข้าใจคำว่า ', 'utf-8')
            sendMessage = sendMessage+event.message.text
        
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=sendMessage))


if __name__ == "__main__":
    app.run(debug=config.app['debug'], threaded=True)
