from twisted.internet.protocol import Factory
from irc_protocol import IRCProtocol

class ChatServer(Factory):

	def __init__(self):
		self.users = {} # maps user names to Chat instances
		self.rooms = {} # mapr rooms to Chat isntances

	def buildProtocol(self, addr):
		return IRCProtocol(self.users, self.rooms)