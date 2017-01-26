from twisted.internet.protocol import Factory
from twisted.internet import reactor
from twisted.words.protocols.irc import IRC

NUL = chr(0) #\x00
CR = chr(0o15) #\r
NL = chr(0o12) #\n
LF = NL #\n
SPC = chr(0o40) #' '


def parsemsg(s):
	prefix = ''
	trailing = []
	if not s:
		raise IRCBadMessage("Empty line.")
	if s[0] == '/':
		prefix = '/'
		args = s[1:].split()
	else:
		args = s.split()
	command = args.pop(0)
	return prefix, command, args

class User(IRC):
	OUTPUT_DENOTER = "<= "
	INPUT_DENOTER = "=> "

	def __init__(self, users, rooms):
		self.users = users
		self.rooms = rooms
		self.name = None
		self.state = "GETNAME"

	def sendToClient(self,data):
		self.transport.write(self.OUTPUT_DENOTER + data + "\n")

	def connectionMade(self):
		self.sendToClient("Welcome to Rakuten Games chat server")
		self.sendToClient("Login name?")

	def connectionLost(self, reason):
		if self.name in self.users:
			del self.users[self.name]

	def dataReceived(self,data):
		if data[0] == '/':
			self.handle_Command(data)
			return 

		if self.state == "GETNAME":
			self.handle_GETNAME(data.rstrip())
		else:
			self.handle_CHAT(data.rstrip())

	def handle_Command(self,data):
		lines = (self.buffer + data).split(LF)
		# Put the (possibly empty) element after the last LF back in the
		# buffer
		self.buffer = lines.pop()

		for line in lines:
			if len(line) <= 2:
				# This is a blank line, at best.
				continue
			if line[-1] == CR:
				line = line[:-1]
			prefix, command, params = parsemsg(line)
			# mIRC is a big pile of doo-doo
			command = command.upper()
			# DEBUG: log.msg( "%s %s %s" % (prefix, command, params))

			IRC.handleCommand(self,command, prefix, params)

	def handle_GETNAME(self, name):
		if name in self.users:
			self.sendToClient("Sorry, name taken.")
			return
		self.sendToClient("Welcome {}!".format(name))
		self.name = name
		self.users[name] = [self,None]
		self.state = "CHAT"

	def handle_CHAT(self, message):
		message = "<%s> %s" % (self.name, message)
		for name, protocol in self.users.iteritems():
			if protocol[0] != self:
				protocol[0].sendLine(message)

	def irc_unknown(self, prefix, command, params):
		self.sendToClient("{}, {}, {}, IRC UNKNOWN".format(prefix, command, params))

	def irc_ROOMS(self, prefix, params):
		self.sendToClient("Active rooms are:")
		for room_name,room in self.rooms.iteritems():
			self.sendToClient("*" + room_name + " (" + str(len(room.users)) + ")")
		self.sendToClient("end of list.")

	def irc_JOIN(self, prefix, params):
		if not params:
			self.sendToClient("Please use : /join <room-name>")
		else:
			self.sendToClient("entering room: {}".format(params[0]))
			self.joinRoom(params[0])
			listUsers(params[0])

	def listUsers(self,room_name):
		for user in self.rooms[room_name].users:
			if user == self.name:
				self.sendToClient("* " + user + "(** this is you)")
			else:
				self.sendToClient("* " + user)

	def joinRoom(self, room_name):
		if room_name in self.rooms:
			room = self.rooms[room_name]
		else:
			room = Room(room_name)
			self.rooms[room_name] = room
		self.users[self.name][1] = room
		room.addUser(self.name)


class ChatServer(Factory):

	def __init__(self):
		self.users = {} # maps user names to Chat instances
		self.rooms = {} # mapr rooms to Chat isntances

	def buildProtocol(self, addr):
		return User(self.users, self.rooms)

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

reactor.listenTCP(55555, ChatServer())
reactor.run()