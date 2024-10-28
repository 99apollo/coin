import database_wrapper

userDbName = "users"

class UserTransaction:
	def createUser(name, password):
		hashedName = hash(name)
		hashedPassword = hash(password)
		moneyBalance = 0
		coinBalance = 0
		currentOffers = 0
		user = {"username" : hashedName, "password" : hashedPassword, "money" : moneyBalance, "coins" : coinBalance, "offers" : currentOffers}
		DatabaseWrapper.post(userDbName, user)

	def loginUser(name, password):
		hashedName = hash(name)
		hashedPassword = hash(name)
		user = {"username" : hashedName, "password" : hashedPassword}
		return DatabaseWrapper.find_one(userDbName, user)
