#main.py
from flask import Flask, render_template, request, send_from_directory, redirect, url_for, session, flash, jsonify
from roboflow import Roboflow
from PIL import Image
from gtts import gTTS
import os
from db import Database  # db.py dosyasını ekledik
import secrets
from datetime import datetime


app = Flask(__name__)
app.debug = False
app.config['MYSQL_CONNECT_TIMEOUT'] = 3600
app.config['IMAGES_FOLDER'] = 'images'
app.secret_key = secrets.token_hex(16)


db = Database()
db.init_app(app)


rf = Roboflow(api_key="fcgvx4oACfbJ4Dxrf5NZ")
project = rf.workspace().project("deneme2-mkqfr")
model = project.version(7).model

uploads_folder = os.path.join(app.config['IMAGES_FOLDER'], 'uploads')
detected_folder = os.path.join(app.config['IMAGES_FOLDER'], 'detected')

# ... (diğer kısımlar aynı kalacak)

# Eğer images klasörü yoksa oluştur
if not os.path.exists(app.config['IMAGES_FOLDER']):
    os.makedirs(app.config['IMAGES_FOLDER'])


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Veritabanındaki kullanıcıları kontrol etmek için bir sorgu yapın
        connection = db.get_connection()
        cursor = connection.cursor()

        try:
            cursor.execute('SELECT * FROM nesnetespit.kullanicilar WHERE kullaniciadi = %s AND sifre = %s', (username, password))
            user = cursor.fetchone()

            if user:
                # Kullanıcı adı ve şifre doğruysa oturumu başlat
                session['username'] = username
                return redirect(url_for('index'))  # Başarılı giriş, Nesne Tespit Ekranı'na yönlendir.

            # Giriş başarısızsa hata mesajı ile birlikte login sayfasına yönlendir.
            flash('Hatalı kullanıcı adı veya şifre.', 'error')
            return redirect(url_for('login'))

        except Exception as e:
            print("MySQL Hatası:", str(e))
            flash('Bir hata oluştu, lütfen daha sonra tekrar deneyin.', 'error')
            connection.rollback()  # Hata durumunda işlemi geri al

    return render_template('login.html')


@app.route('/logout')
def logout():
    # Oturumu temizle
    session.clear()
    # Ana sayfaya yönlendir
    return redirect(url_for('login'))


# Nesne Tespit Ekranı
@app.route('/')
def index():
    # Bu kısım kullanıcının giriş yapmış olup olmadığını kontrol eder
    if 'username' in session:
        # Kullanıcı giriş yapmışsa Nesne Tespit Ekranı'nı göster
        username = session['username']
        tespitler = get_kullanici_tespitler(username)

        current_user_id = session.get('user_id')

        return render_template('index.html', tespitler=tespitler, current_user_id=current_user_id)
    else:
        # Kullanıcı giriş yapmamışsa login sayfasına yönlendir
        return redirect(url_for('login'))

# Statik dosyaları servis etmek için
@app.route('/images/<path:folder>/<path:filename>')
def serve_images(folder, filename):
    return send_from_directory(os.path.join(app.config['IMAGES_FOLDER'], folder), filename)

# Nesne tespiti fonksiyonunu tanımla
def perform_object_detection(image_path_original,image_path_resized):
    result = model.predict(image_path_resized, confidence=50, overlap=30)
    return result

class_translation = {
    "akilli telefon": "smartphone",
    "bozuk para": "coin",
    "cuzdan": "wallet",
    "dizustu bilgisayar": "laptop",
    "fare-ekipman-": "mouse(equipment)",
    "gozluk": "glasses",
    "kalem": "pen",
    "kitap": "book",
    "klavye": "keyboard",
    "kol saati": "watch",
    "kolye": "necklace",
    "kulaklik": "headphones",
    "makas": "scissors",
    "monitor": "monitor",
    "pet sise": "pet bottle",
    "priz": "socket",
    "spor ayakkabi": "sports shoes",
    "sirt cantasi": "backpack",
    "usb bellek": "USB flash drive",
    "uzaktan kumanda": "remote control",
}


# Yüklenen resmi nesne tespiti yapmak için
@app.route('/object_detection', methods=['POST'])
def object_detection():
    class_id = None  # class_id'yi başlangıçta tanımla
    confidence = None
    new_index=""

    if request.method == 'POST':
        try:
            # Eski dosyaları temizle
            for file_name in os.listdir(detected_folder):
                file_path = os.path.join(detected_folder, file_name)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            for file_name in os.listdir(uploads_folder):
                file_path = os.path.join(uploads_folder, file_name)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            # Flash belleğini temizle
            flash('')


            # Yüklü olan resmi al
            uploaded_image = request.files['image']
            image_path_original = os.path.join(uploads_folder, "uploaded_image.jpg")
            uploaded_image.save(image_path_original)

            # Resmi %50 oranında küçült
            image = Image.open(image_path_original)
            width, height = image.size
            new_size = (int(width * 0.5), int(height * 0.5))
            resized_image = image.resize(new_size)
            image_path_resized = os.path.join(uploads_folder, "uploaded_image_resized.jpg")
            resized_image.save(image_path_resized)

            detection_result = perform_object_detection(image_path_original, image_path_resized)

            detected_image_path = os.path.join(detected_folder, "detected_image.jpg")
            detection_result.save(detected_image_path)

            # Kullanıcının tespit ettiği nesneleri veritabanından çek
            username = session['username']
            tespitler = get_kullanici_tespitler(username)


                        # Nesne tespiti sonuçlarını işle
            object_results = []
            for prediction in detection_result.predictions:

                class_name = prediction['class']
                class_translation_list = list(class_translation.keys())

                if class_name in class_translation:
                    index = class_translation_list.index(class_name)
                    new_index=index+1
                    print("Index:", index)
                else:
                    print("Class not found in translation dictionary.")

                confidence = round(prediction['confidence'], 2)#virgülden sonraki 2 basamak
                english_class = class_translation.get(class_name, 'Translation Not Found')

                save_detection(new_index,detected_image_path, confidence)

                # Nesne sonuçları listeleme
                object_results.append({
                    'class': class_name,
                    'confidence': confidence,
                    'english_class': english_class
                })


            result_template = render_template('result.html', object_results=object_results, detected_image_path=detected_image_path, tespitler=tespitler)



            # Sonuçları şablon ile göster
            return result_template

        except Exception as e:
            print("Hata:", str(e))
            flash('Bir hata oluştu, lütfen daha sonra tekrar deneyin.', 'error')

    return  'Invalid Request'

@app.route('/save_detection', methods=['POST'])
def save_detection(new_index, detected_image_path, confidence):
    connection = None
    try:
        connection = db.get_connection()
        cursor = connection.cursor()

        # Kullanıcının ID'sini al
        username = session['username']
        cursor.execute('SELECT id FROM nesnetespit.kullanicilar WHERE kullaniciadi = %s', (username,))
        user_id = cursor.fetchone()['id']

        # Tespit edilen nesneyi veritabanına ekle
        cursor.execute(
            'INSERT INTO nesnetespit.tespitedilennesneler (kullanici_id, nesne_id, resim, tespit_zamani,  oran) VALUES (%s, %s, %s, %s, %s)',
            (user_id, new_index, detected_image_path, datetime.now(),  confidence)
        )

        # Veritabanı değişikliklerini kaydet
        connection.commit()
        flash('Nesne tespit bilgileri başarıyla kaydedildi.', 'success')

    except Exception as e:
        print("MySQL Hatası:", str(e))
        flash('Bir hata oluştu, lütfen daha sonra tekrar deneyin.', 'error')

    return 'Invalid Request'

def get_kullanici_tespitler(username):
    connection = db.get_connection()
    cursor = connection.cursor()

    cursor.execute('''
        SELECT n.nesne_adi, n.ceviri, t.tespit_zamani, t.oran
        FROM nesnetespit.tespitedilennesneler AS t
        JOIN nesnetespit.nesneler AS n ON t.nesne_id = n.id
        JOIN nesnetespit.kullanicilar AS k ON t.kullanici_id = k.id
        WHERE k.kullaniciadi = %s
    ''', (username,))

    tespitler = cursor.fetchall()
    return tespitler

@app.route('/delete_detection', methods=['POST'])
def delete_detection():
    try:
        user_id = session.get('user_id')  # session'dan kullanıcı ID'sini al
        detection_id = request.json.get('detection_id')

        # Tespit edilen nesneyi veritabanından sil
        connection = db.get_connection()
        cursor = connection.cursor()
        cursor.execute('DELETE FROM nesnetespit.tespitedilennesneler WHERE nesne_id = %s AND kullanici_id = %s', (detection_id, user_id))
        connection.commit()
        print(detection_id, user_id)

        # Silme işlemi başarılıysa başarı durumu gönderin
        return jsonify({'status': 'success'})

    except Exception as e:
        print("Hata:", str(e))
        connection.rollback()  # Hata durumunda işlemi geri al
        return jsonify({'status': 'error'})

@app.route('/speak', methods=['POST'])
def speak_english_translation():
    if request.method == 'POST':
        english_text = request.form.get('english_text')

        # Ses dosyasını oluştur
        tts = gTTS(english_text, lang='en')
        tts_file_path = os.path.join(app.config['IMAGES_FOLDER'], 'english_translation.mp3')
        tts.save(tts_file_path)

        # Oluşturulan ses dosyasını çalar
        os.system(f"start {tts_file_path}")  # Windows için

        return 'OK'

    return 'Invalid Request'

if __name__ == '__main__':
    app.run(debug=True)
