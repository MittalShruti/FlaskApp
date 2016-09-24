#!/usr/bin/env python

import logging
from flask import Flask, request, jsonify
from flaskext.mysql import MySQL
import urllib, cStringIO
import numpy  
from PIL import Image
import keras
from keras.models import load_model
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
@app.route("/")
def Authenticate():
    trained_model = '/var/www/FlaskApp/FlaskApp/shallowlargedropout.h5'  #trained on images without listup watermark
    mysql = MySQL()
    app.config['MYSQL_DATABASE_USER'] = 'saurabh'
    app.config['MYSQL_DATABASE_PASSWORD'] = 'listup'
    app.config['MYSQL_DATABASE_DB'] = 'trovo'
    app.config['MYSQL_DATABASE_HOST'] = '173.194.108.135'
    mysql.init_app(app)
    model = keras.models.load_model(trained_model)
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT image_filename, productid FROM product_image WHERE date(created_at)=DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)")
    rows = cursor.fetchall()
    pre = 0
    for row in rows:
        url = 'https://storage.googleapis.com/trovo-product/'+ row[0]
        file = cStringIO.StringIO(urllib.urlopen(url).read())
        try:
            img = Image.open(file)
            img = img.resize((32,32))
            im = numpy.array(img)
            r = im[:,:,0] #Slicing to get R data
            g = im[:,:,1] #Slicing to get G data
            b = im[:,:,2] #Slicing to get B data
            out = numpy.array([[r] + [g] + [b]], numpy.uint8) 
            out1 = out.astype('float32')/255
            predictions = model.predict_classes(out1)
            if predictions[0]==0: #OLX-watermarked
                pre = pre + 1
                cursor.execute("""UPDATE product SET has_olx_logo=%s WHERE productid=%s""",(1,row[1],))
                conn.commit()
        except Exception:
            pass
    return str(pre)+' products have OLX watermark, out of scanned '+str(len(rows))+ ' products'
@app.before_first_request
def initialize():
    scheduler = BackgroundScheduler()
    scheduler.add_job(Authenticate,'interval',
    days=1,
    start_date='2016-09-13 04:00:00',
    replace_existing=True)
    scheduler.start()

if __name__ == "__main__":
# Shut down the scheduler when exiting the app
#    atexit.register(lambda: scheduler.shutdown())
    app.run()
