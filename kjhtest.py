from flask import Flask, session, request, render_template, redirect, jsonify, url_for
from bson import ObjectId
from pymongo import MongoClient
from datetime import datetime
import requests
import threading
import time

app = Flask(__name__)

app.secret_key = 'your_secret_key'
client = MongoClient("mongodb+srv://99apollo:kjh990319!@cluster0.664uk.mongodb.net/")
db = client['test_db']
user_collection = db['users']
initcoin_collection = db["initcoin"]
transition_collection = db['transition']
history_collection = db['history']

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

# Your existing routes remain unchanged...
@app.route("/")
def main():
    # Fetch recent transitions and coin data
    transitions = []
    all_transitions = transition_collection.find()
    
    coin_data = initcoin_collection.find_one()
    coin = coin_data['coin']
    price = coin_data['price']
    
    # Fetch recent transitions
    recent_transitions = list(history_collection.find().sort('_id', -1).limit(10))
    
    # Prepare recent transitions for rendering
    recent_transitions_serializable = []
    for transition in recent_transitions:
        recent_transitions_serializable.append({
            'seller_id': transition['seller_id'],
            'buyer_id': transition['buyer_id'],
            'selled_coin_number': transition['selled_coin_number'],
            'price': int(transition['price']),
            'timestamp': transition['timestamp']
        })
    
    name = session.get('name')
    if name:
        user = user_collection.find_one({'id': session['name']})
        
        for transition in transition_collection.find({'user_id': name}):
            transitions.append({
                '_id': transition['_id'],
                'user_id': transition['user_id'],
                'coin_count': transition['coin_count'],
                'coin_price': int(transition['price_per_coin'])
            })
        
        return render_template("mainpage.html", name=name, money=user['money'], coin=user['coin'], server_coin=coin, server_price=price, transitions=transitions, all_transitions=all_transitions, recent_transitions=recent_transitions_serializable, coin_prices=latest_coin_prices)
    else:
        return render_template("mainpage.html", name="guest", server_coin=coin, server_price=price, all_transitions=all_transitions, recent_transitions=recent_transitions_serializable, coin_prices=latest_coin_prices)

@app.route("/signup")
def start():
    return render_template("signin.html")

@app.route('/login', methods=['POST'])
def login():
    # form data extract - to be handled by the screen classes
    id = request.form['ID']
    password = request.form['password']
    
    # ID test for duplicated in MongoDB
	# to be handled by the database wrapper
    user = user_collection.find_one({'id': id}) 
    if user is not None: #transaction script logic
        return redirect("/alert") 

    # Save User info in MongDB
	# again handled by the transaction script - change into handling the hashed values
    user = {
        'id': id,
        'password': password,
        'money':0,
        'coin':0,
        'selling_coin':0
    }
    user_collection.insert_one(user)

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

    
@app.route('/signin', methods=['POST'])
def signin():
    #Form data extract
	#for id and password check up - use hashed values
	#for session - only plain text

    id = request.form['ID']
    password = request.form['password']
    
    # Find ID from MongoDB
    user = user_collection.find_one({'id': id, 'password': password})
    
    if user:
        # Save User ID as session
        session['name'] = id
        return redirect("/")
    else:
        return '<script>alert("아이디 또는 비밀번호가 일치하지 않습니다.");window.location.href="/";</script>'


@app.route('/charge', methods=['POST'])
def charge():
    # Form data extract
    amount = request.form.get('amount')

    # Check if amount is not provided or left blank
    if amount is None or amount.strip() == '':
        return '<script>alert("충전할 금액을 입력해주세요!");window.location.href="/";</script>'

    try:
        # Convert amount to an integer
        amount = int(amount)
    except ValueError:
        return '<script>alert("유효한 금액을 입력해주세요!");window.location.href="/";</script>'

    # currentuser data update
    user_collection.update_one({'id': session['name']}, {'$inc': {'money': amount}})

    # finsh message
    return '<script>alert("충전이 완료되었습니다");window.location.href="/";</script>'

@app.route('/withdraw', methods=['POST'])
def withdraw():
    # Get the withdrawal amount from the form data
    withdraw_amount = float(request.form.get('withdraw_amount'))

    # Get the user document
    user = user_collection.find_one({'id': session['name']})

    # Check if the withdrawal amount is valid
    if withdraw_amount <= 0:
        return '<script>alert("유효한 출금 금액을 입력해주세요."); window.location.href="/";</script>'

    if withdraw_amount > user['money']:
        return '<script>alert("보유한 금액보다 많은 금액을 출금할 수 없습니다."); window.location.href="/";</script>'

    # Update the user's money in the database
    user_collection.update_one({'id': session['name']}, {'$inc': {'money': -withdraw_amount}})

    return '<script>alert("출금이 완료되었습니다."); window.location.href="/";</script>'

@app.route("/buyservercoin", methods=["POST"])
def buyservercoin():
    # Form data extract
    coincount = request.form.get('coincount')

    # Check if coincount is not provided or left blank
    if coincount is None or coincount.strip() == '':
        return '<script>alert("구매할 코인 개수를 입력해주세요!");window.location.href="/";</script>'

    try:
        # Convert coincount to an integer
        coincount = int(coincount)
    except ValueError:
        return '<script>alert("유효한 코인 개수를 입력해주세요!");window.location.href="/";</script>'

    # Check if coincount is 0
    if coincount == 0:
        return '<script>alert("구매할 코인 개수는 0개일 수 없습니다!");window.location.href="/";</script>'

    # count Coin in server
    initcoin = initcoin_collection.find_one()
    server_coincount = initcoin['coin']

    # buyable coin count
    affordable_coincount = min(coincount, server_coincount)
    
    # Cannot buy more coin than its remainning
    if affordable_coincount < coincount:
        return '<script>alert("서버에 남은 코인 수보다 많은 코인을 구매할 수 없습니다!");window.location.href="/";</script>'

    # total price of coin
    affordable_price = affordable_coincount * initcoin['price']

    # get user doucment
    user = user_collection.find_one({'id': session['name']})

    # if is possible
    if user['money'] >= affordable_price:
        # update user doucment
        user_collection.update_one({'id': session['name']}, {'$inc': {'money': -affordable_price, 'coin': affordable_coincount}})
        now = datetime.now()
        # initcoin doucment update
        initcoin_collection.update_one({}, {'$inc': {'coin': -affordable_coincount}})
        history={
            'buyer_id':session['name'],
            'seller_id':"server",
            'selled_coin_number':coincount,
            'price': 100,
            'timestamp': now
        }
        history_collection.insert_one(history)

        return '<script>alert("구매가 완료되었습니다!");window.location.href="/";</script>'
    else:
        return '<script>alert("돈이 부족합니다!");window.location.href="/";</script>'


@app.route("/sellusercoin", methods=["POST"])
def sellusercoin():
    # Form data extract
    coincount = request.form.get('coincount')
    sellprice = request.form.get('sellprice')

    # Check if coincount or sellprice is not provided or left blank
    if coincount is None or coincount.strip() == '' or sellprice is None or sellprice.strip() == '':
        return '<script>alert("코인 수와 판매 가격을 입력해주세요!");window.location.href="/";</script>'

    try:
        coincount = int(coincount)
        sell_price = float(sellprice)
    except ValueError:
        return '<script>alert("유효한 코인 수와 판매 가격을 입력해주세요!");window.location.href="/";</script>'

    # Get user document
    user = user_collection.find_one({'id': session['name']})
    selling_coin = user['selling_coin']

    # Cannot sell more coin than the user has
    if user['coin'] < coincount + selling_coin:
        return '<script>alert("보유 코인보다 많은 코인을 판매할 수 없습니다!");window.location.href="/";</script>'
    else:
        # timestamp
        now = datetime.now()
        user_collection.update_one({'id': session['name']}, {'$set': {'selling_coin': selling_coin + coincount}})
        # save data to transition collection
        transition = {
            'user_id': session['name'],
            'type': 'sell',
            'coin_count': coincount,
            'price_per_coin': sell_price,
            'total_price': coincount * sell_price,
            'timestamp': now
        }
        transition_collection.insert_one(transition)

        return '<script>alert("판매 신청이 완료되었습니다!");window.location.href="/";</script>'

@app.route("/delete_transition/<transition_id>", methods=["POST"])
def delete_transition(transition_id):
    # get data from MongoDB
    item=transition_collection.find_one({'_id': ObjectId(transition_id)})
    item2=item['coin_count']

    # deleted transition
    result = transition_collection.delete_one({'_id': ObjectId(transition_id)})

    if result.deleted_count > 0:
        user_collection.update_one({'id': session['name']}, {'$inc':{'selling_coin':-item2}})
        # deleted
        return '<script>alert("판매 기록이 삭제되었습니다."); window.location.href="/";</script>'
    else:
        # failed
        return '<script>alert("판매 기록 삭제에 실패했습니다."); window.location.href="/";</script>'
    
@app.route("/buyusercoin", methods=["POST"])
def buyusercoin():
    # Form data extraction
    transition_id = request.form['transition_id']

    # Retrieve the transition document from the transition collection
    transition = transition_collection.find_one({'_id': ObjectId(transition_id)})
    if not transition:
        return '<script>alert("유효하지 않은 거래입니다!");window.location.href="/";</script>'
    
    buyer_id = session['name']
    seller_id = transition['user_id']
    coincount = transition['coin_count']
    price = transition['price_per_coin']
    
    # Get the buyer and seller documents from the user collection
    buyer = user_collection.find_one({'id': buyer_id})
    seller = user_collection.find_one({'id': seller_id})
    if not buyer or not seller:
        return '<script>alert("구매자 또는 판매자 정보를 찾을 수 없습니다!");window.location.href="/";</script>'
    
    # Calculate the total cost of the purchase
    total_cost = coincount * price
    
    # Check if the buyer has enough money to make the purchase
    if buyer['money'] >= total_cost:
        # Update buyer's information
        user_collection.update_one({'id': buyer_id}, {'$inc': {'coin': coincount, 'money': -total_cost}})
        # Update seller's information
        user_collection.update_one({'id': seller_id}, {'$inc': {'coin': -coincount, 'money': total_cost, 'selling_coin': -coincount}})
        now = datetime.now()
        # Create a history document
        history = {
            'buyer_id': buyer_id,
            'seller_id': seller_id,
            'selled_coin_number': coincount,
            'price': price,
            'timestamp': now
        }
        # Insert the history document into the history collection
        history_collection.insert_one(history)
        
        # Delete the transition document from the transition collection
        transition_collection.delete_one({'_id': ObjectId(transition_id)})
        
        return '<script>alert("구매가 완료되었습니다!");window.location.href="/";</script>'
    else:
        return '<script>alert("잔액이 부족하여 구매할 수 없습니다!");window.location.href="/";</script>'
        

    
if __name__ == '__main__':
    app.run(debug=True)
