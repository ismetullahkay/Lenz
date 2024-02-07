#db.py
from flask_mysqldb import MySQL

class Database:
    mysql = MySQL()

    @staticmethod
    def init_app(app):
        app.config['MYSQL_CONNECT_TIMEOUT'] = 1800

        app.config['MYSQL_HOST'] = 'localhost'
        app.config['MYSQL_PORT'] = 3306
        app.config['MYSQL_USER'] = 'root'
        app.config['MYSQL_PASSWORD'] = '1234'
        app.config['MYSQL_DB'] = 'nesnetespit'
        app.config['MYSQL_CHARSET'] = 'utf8'
        app.config['MYSQL_CURSORCLASS'] = "DictCursor"

        Database.mysql.init_app(app)

    @staticmethod
    def get_connection():
        return Database.mysql.connection

    @staticmethod
    def get_cursor():
        return Database.mysql.connection.cursor()

    @staticmethod
    def before_request():
     try:
         # Her istek öncesi bağlantıyı açın
         Database.mysql_db.connection = Database.mysql_db.connect()
     except Exception as e:
         print("MySQL Connection Error:", str(e))

    @staticmethod
    def teardown_request(exception=None):
        try:
         # Her istek sonrası bağlantıyı kapatın
            if hasattr(Database.mysql_db, 'connection') and Database.mysql_db.connection:
                Database.mysql_db.connection.close()
        except Exception as e:
            print("MySQL Connection Closing Error:", str(e))

