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

class ChatServer(IRC):
	OUTPUT_DENOTER = "<= "
	INPUT_DENOTER = "=> "

	def __init__(self, users):
		self.users = users
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
			self.sendToClient("Sorry, name taken")
			return
		self.sendToClient("Welcome, {}!".format(name))
		self.name = name
		self.users[name] = self
		self.state = "CHAT"

	def handle_CHAT(self, message):
		message = "<%s> %s" % (self.name, message)
		for name, protocol in self.users.iteritems():
			if protocol != self:
				protocol.sendLine(message)

	def irc_unknown(self, prefix, command, params):
		print "%s, %s, %s, IRC UNKNOWN" % (prefix, command, params)


class ChatServerFactory(Factory):

	def __init__(self):
		self.users = {} # maps user names to Chat instances

	def buildProtocol(self, addr):
		return ChatServer(self.users)


reactor.listenTCP(55555, ChatServerFactory())
reactor.run()