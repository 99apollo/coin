from flask import Flask, session, request, render_template, redirect, jsonify, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine
from datetime import datetime
import requests
import threading
import time
import bcrypt
import os
from sqlalchemy import text
app = Flask(__name__)
app.secret_key = os.urandom(24)

# 로컬 MySQL 데이터베이스 설정 (일반 데이터)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://your_username:your_password@localhost/testdb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 원격 MySQL 데이터베이스 설정 (User 데이터 전용)
remote_engine = create_engine('mysql+mysqlconnector://remote_user:remote_password@3.35.47.173/userdb')
RemoteSession = scoped_session(sessionmaker(bind=remote_engine))

# 로컬 DB 모델
class InitCoin(db.Model):
    __tablename__ = 'init_coin'
    id = db.Column(db.Integer, primary_key=True)
    coin = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)

class Transition(db.Model):
    __tablename__ = 'transition'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(80), nullable=False)
    coin_count = db.Column(db.Float, nullable=False)
    price_per_coin = db.Column(db.Float, nullable=False)

class History(db.Model):
    __tablename__ = 'history'
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.String(80), nullable=False)
    buyer_id = db.Column(db.String(80), nullable=False)
    selled_coin_number = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# 원격 DB 모델 (User 로그인 관련 모델)
class User:
    def __init__(self, id, password, money=0, coin=0, selling_coin=0):
        self.id = id
        self.password = password
        self.money = money
        self.coin = coin
        self.selling_coin = selling_coin

    @staticmethod
    def get_user_by_id(user_id):
        with RemoteSession() as session:
            result = session.execute(text("SELECT * FROM User WHERE id = :id"), {'id': user_id}).fetchone()
            if result:
                return User(id=result.id, password=result.password, money=result.money, coin=result.coin, selling_coin=result.selling_coin)
            return None

    @staticmethod
    def add_user(user_id, hashed_password, money=0, coin=0, selling_coin=0):
        with RemoteSession() as session:
            session.execute(
                "INSERT INTO User (id, password, money, coin, selling_coin) VALUES (:id, :password, :money, :coin, :selling_coin)",
                {'id': user_id, 'password': hashed_password, 'money': money, 'coin': coin, 'selling_coin': selling_coin}
            )
            session.commit()

# Global variable to store the latest coin prices
latest_coin_prices = []

def update_coin_prices():
    global latest_coin_prices
    while True:
        try:
            # Fetch latest coin prices from the API
            server_url = "https://api.upbit.com"
            params = {"markets": "KRW-BTC,KRW-ETH"}
            res = requests.get(server_url + "/v1/ticker", params=params)
            if res.status_code == 200:
                latest_coin_prices = res.json()
            else:
                print("Failed to fetch prices:", res.status_code)
        except Exception as e:
            print("Error fetching prices:", e)
        
        time.sleep(1)  # Sleep for 1 second before the next update

# Start the background thread for updating coin prices
threading.Thread(target=update_coin_prices, daemon=True).start()

@app.route('/api/coin-prices', methods=['GET'])
def get_coin_prices():
    return jsonify(latest_coin_prices)

@app.route("/")
def main():
    transitions = []
    
    # Fetch initial coin data
    coin_data = InitCoin.query.first()
    coin = coin_data.coin if coin_data else 0
    price = coin_data.price if coin_data else 0

    # Fetch recent transitions
    recent_transitions = History.query.order_by(History.id.desc()).limit(10).all()
    recent_transitions_serializable = [
        {
            'seller_id': transition.seller_id,
            'buyer_id': transition.buyer_id,
            'selled_coin_number': transition.selled_coin_number,
            'price': transition.price,
            'timestamp': transition.timestamp
        }
        for transition in recent_transitions
    ]

    name = session.get('name')
    if name:
        user = User.get_user_by_id(name)
        for transition in Transition.query.filter_by(user_id=name).all():
            transitions.append({
                'id': transition.id,
                'user_id': transition.user_id,
                'coin_count': transition.coin_count,
                'coin_price': transition.price_per_coin
            })
        
        return render_template("mainpage.html", name=name, money=user.money, coin=user.coin, server_coin=coin, server_price=price, transitions=transitions, recent_transitions=recent_transitions_serializable, coin_prices=latest_coin_prices)
    else:
        return render_template("mainpage.html", name="guest", server_coin=coin, server_price=price, recent_transitions=recent_transitions_serializable, coin_prices=latest_coin_prices)

@app.route("/signup")
def start():
    return render_template("signin.html")

@app.route('/login', methods=['POST'])
def login():
    id = request.form['ID']
    password = request.form['password']
    
    # User 모델을 통해 원격 DB에서 사용자 확인
    user = User.get_user_by_id(id)
    if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        session['name'] = id
        return redirect("/")
    else:
        return '<script>alert("아이디 또는 비밀번호가 일치하지 않습니다.");window.location.href="/";</script>'

@app.route('/signup', methods=['POST'])
def signup():
    id = request.form['ID']
    password = request.form['password']

    user = User.get_user_by_id(id)
    if user:
        return redirect("/alert")

    # 비밀번호 해싱 후 원격 DB에 저장
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    User.add_user(id, hashed_password, money=0, coin=0, selling_coin=0)  # 초기 값 설정

    session['name'] = id
    return redirect("/")

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('name', None)
    return redirect("/")

@app.route('/alert')
def alert():
    return '''
    <script>
        function showAlert() {
            alert('중복된 아이디입니다.');
            window.location.replace('/');
        }
        showAlert();
    </script>
    '''

@app.route('/charge', methods=['POST'])
def charge():
    amount = request.form.get('amount')

    if amount is None or amount.strip() == '':
        return '<script>alert("충전할 금액을 입력해주세요!");window.location.href="/";</script>'

    try:
        amount = int(amount)
    except ValueError:
        return '<script>alert("유효한 금액을 입력해주세요!");window.location.href="/";</script>'

    user = User.get_user_by_id(session['name'])
    user.money += amount
    db.session.commit()
    return '<script>alert("충전이 완료되었습니다");window.location.href="/";</script>'

@app.route('/withdraw', methods=['POST'])
def withdraw():
    withdraw_amount = float(request.form.get('withdraw_amount'))
    user = User.get_user_by_id(session['name'])

    if withdraw_amount <= 0:
        return '<script>alert("유효한 출금 금액을 입력해주세요."); window.location.href="/";</script>'

    if withdraw_amount > user.money:
        return '<script>alert("보유한 금액보다 많은 금액을 출금할 수 없습니다."); window.location.href="/";</script>'

    user.money -= withdraw_amount
    db.session.commit()
    return '<script>alert("출금이 완료되었습니다."); window.location.href="/";</script>'

@app.route("/buyservercoin", methods=["POST"])
def buyservercoin():
    coincount = request.form.get('coincount')

    if coincount is None or coincount.strip() == '':
        return '<script>alert("구매할 코인 개수를 입력해주세요!");window.location.href="/";</script>'

    try:
        coincount = int(coincount)
    except ValueError:
        return '<script>alert("유효한 코인 개수를 입력해주세요!");window.location.href="/";</script>'

    if coincount <= 0:
        return '<script>alert("구매할 코인 개수는 0개 이상이어야 합니다!");window.location.href="/";</script>'

    coin_data = InitCoin.query.first()
    if coin_data is None:
        return '<script>alert("서버에서 코인 데이터가 없습니다!");window.location.href="/";</script>'
    
    server_coincount = coin_data.coin
    server_price = coin_data.price

    total_price = coincount * server_price

    user = User.get_user_by_id(session['name'])
    
    # Check if user has enough money
    if user.money < total_price:
        return '<script>alert("잔액이 부족합니다!");window.location.href="/";</script>'

    # Update user's money and coins
    user.money -= total_price
    user.coin += coincount

    # Update server's coin count
    coin_data.coin -= coincount

    # Create a transition record
    new_transition = Transition(user_id=user.id, coin_count=coincount, price_per_coin=server_price)
    db.session.add(new_transition)

    # Create a history record
    new_history = History(seller_id='server', buyer_id=user.id, selled_coin_number=coincount, price=total_price)
    db.session.add(new_history)

    # Commit all changes to the database
    db.session.commit()

    return '<script>alert("코인 구매가 완료되었습니다.");window.location.href="/";</script>'

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # 로컬 DB에 대한 테이블 생성
    app.run(host="0.0.0.0", port=5000, debug=True)
