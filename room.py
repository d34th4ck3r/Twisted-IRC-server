class Room:

	def __init__(self, name):
		self.name = name
		self.users = []

	def addUser(self, user):
		if user in self.users:
			print "User already in room {}".format(self.name)
		else:
			self.users = self.users + [user]

	def delUser(self, user):
		if user in self.users:
			self.users.remove(user)
		else:
			print "User not in room {}".format(self.name)