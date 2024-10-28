import database_wrapper

marketDbName = "market"

class MarketTransaction:
	def buyFromMarket(amount) #who is going to buy? does he have enough money?
		amountAvailable = DatabaseWrapper.find_one(marketDbName, "amount")
		pass

#TO BE IMPLEMENTED
