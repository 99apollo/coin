import database_wrapper



class MainScreen:
	def __init__(self, session):
		this.session = session
		#insert some initial variables


	def render(self):
		name = session.get('name')
		
		coin, price = *this.session.coinTransactions.listInitcoin()
		recent_transitions_serializable, all_transitions = *this.session.coinTransactions.listOffers()
		
		kw_args = dict()
		kw_args['server_coin'] = coin
		kw_args['server_price'] = price
		kw_args['all_transitions'] = all_transitions
		kw_args['recent_transitions'] = recent_transitions_serializable

		if name:
			transitions, user_coin, money = *this.session.userTransactions.listAllInfo(name)
			kw_args['name'] = name
			kw_args['money'] = money
			kw_args['coin'] = user_coin
		
		return render_template("mainpage.html", **kw_args)


	def start(self)
		return render_template("singin.html")


	def login(self, request):
		u_id = request.form['ID']
		password = request.form['password']

		return this.session.userTransactions.loginUser(u_id,password)
		#redirecting in case of wrong password to be solved within server.py
