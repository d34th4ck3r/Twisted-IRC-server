from twisted.words.protocols.irc import IRC
from room import Room

class IRCProtocol(IRC):
	OUTPUT_DENOTER = "<= "

	def __init__(self, users, rooms):
		self.users = users
		self.rooms = rooms
		self.user_name = None
		self.state = "LoggedOut"

	def sendToClient(self,data):
		self.transport.write(self.OUTPUT_DENOTER + data + "\n")

	def broadcastMessage(self,message,room):
		for user in room.users:
			protocol = self.users[user][0]
			if protocol != self:
				protocol.sendLine(message)
	
	def parsemsg(self,s):
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

	def connectionMade(self):
		self.sendToClient("Welcome to Rakuten Games chat server")
		self.sendToClient("Login name?")

	def connectionLost(self, reason):
		if self.user_name in self.users:
			room = self.getRoom(self.user_name)
			if room:
				room.delUser(self.user_name) 
			del self.users[self.user_name]

	def dataReceived(self,data):
		if data.rstrip() == "":
			return
		if self.state == "LoggedOut":
			self.handle_LoggedOut(data.rstrip())
		elif self.state == "LoggedIn":
			self.handle_LoggedIn(data.rstrip())
		elif self.state == "JoinedRoom":
				self.handle_JoinedRoom(data.rstrip())
		else:
			self.sendToClient("In Unknown state : {}".format(self.state))

	def handle_Command(self,data):
		prefix, command, params = self.parsemsg(data)
		# mIRC is a big pile of doo-doo
		command = command.upper()
		# DEBUG: log.msg( "%s %s %s" % (prefix, command, params))

		IRC.handleCommand(self,command, prefix, params)

	def handle_LoggedOut(self, name):
		if name[0] == '/':
				self.sendToClient("You can only use commands after login in. Please enter name to login.")
				return
		if name in self.users:
			self.sendToClient("Sorry, name taken.")
			return
		self.sendToClient("Welcome {}! Use /help to list all commands".format(name))
		self.user_name = name
		self.users[name] = [self,None]
		self.state = "LoggedIn"

	def handle_LoggedIn(self, command):
		if command[0] == '/':
			self.handle_Command(command)
		else:
			self.sendToClient("Please join a room to start chatting using: /join <room-name>")

	def handle_JoinedRoom(self, message):
		if message[0] == '/':
			self.handle_Command(message)
			return
		message = "{}: {}".format(self.user_name, message)
		current_room = self.getRoom(self.user_name)
		self.broadcastMessage(message,current_room)

	def irc_unknown(self, prefix, command, params):
		self.sendToClient("Unknown command {}, please use /help to see available command.".format(command))

	def irc_ROOMS(self, prefix, params):
		if not self.rooms:
			self.sendToClient("No Active rooms. Use /join <room-name> to create new room.")
			return
		self.sendToClient("Active rooms are:")
		for room_name,room in self.rooms.iteritems():
			self.sendToClient("*" + room_name + " (" + str(len(room.users)) + ")")
		self.sendToClient("end of list.")

	def irc_JOIN(self, prefix, params):
		if not params:
			self.sendToClient("Please use : /join <room-name>")
		else:
			if self.users[self.user_name][1]:
				self.leaveCurrentRoom()
			self.sendToClient("entering room: {}".format(params[0]))
			self.joinRoom(params[0])
			self.state = "JoinedRoom"
			self.listUsers(params[0])

	def irc_USERS(self, prefix, params):
		if not params:
			self.sendToClient("All Active users are:")
			for user in self.users:
				if user == self.user_name:
					self.sendToClient("* {} (** this is you), Room : {}".format(user,self.getRoom(user).name if self.getRoom(user) else None ))
				else:
					self.sendToClient("* {}, Room : {}".format(user,self.getRoom(user).name if self.getRoom(user) else None) )
			self.sendToClient("end of list.")
		else:
			if params[0] not in self.rooms:
				self.sendToClient("Room {} not found.".format(params[0]))
			else:
				self.sendToClient("Active users in room {} are:".format(params[0]))
				self.listUsers(params[0])

	def irc_LEAVE(self, prefix, params):
		self.leaveCurrentRoom()
		self.state = "LoggedIn"

	def irc_QUIT(self, prefix, params):
		if self.getRoom(self.user_name):
			self.leaveCurrentRoom()
		del self.users[self.user_name]
		self.transport.loseConnection()

	def irc_HELP(self, prefix, params):
		self.transport.write("List of Commands: \n" +
 			"   rooms - List active rooms \n" +
 			"   users - List all active users or /users <room-name> to see users in a specific room \n" +
 			"   join - Join a chatroom  Ex: /join python \n" +
 			"   leave - Leave the room you are currently in \n"
 			"   msg - Send a private message.  Ex /msg thomas Hi there \n"
 			"   help - Show this help \n"
 			"   quit - Exit the program \n"
			)

	def irc_MSG(self, prefix, params):
		current_room = self.getRoom(self.user_name)
		if not current_room :
			self.sendToClient("You can only send private message to a user in your room. Please join user's room to send them message.")
			return
		if not params:
			self.sendToClient("Usage /msg <user-name> message")
		else:
			if params[0] in self.users and params[0] not in current_room.users:
				self.sendToClient("User {} is not in current room, please join their room to send PM".format(params[0]))
			elif params[0] in current_room.users:
				protocol = self.users[params[0]][0]
				protocol.sendLine("PM from {} : {}".format(self.user_name, " ".join(params[1:])))
			else:
				self.sendToClient("User {} not found".format(params[0]))

	def listUsers(self,room_name):
		for user in self.rooms[room_name].users:
			if user == self.user_name:
				self.sendToClient("* " + user + " (** this is you)")
			else:
				self.sendToClient("* " + user)
		self.sendToClient("end of list.")

	def joinRoom(self, room_name):
		if room_name in self.rooms:
			room = self.rooms[room_name]
		else:
			room = Room(room_name)
			self.rooms[room_name] = room
		self.users[self.user_name][1] = room
		room.addUser(self.user_name)
		self.broadcastMessage("* user has joined the room: {}".format(self.user_name), room)

	def leaveCurrentRoom(self):
		current_room = self.getRoom(self.user_name)
		if current_room:
			self.sendToClient("leaving Room: {}".format(current_room.name))
			current_room.delUser(self.user_name)
			self.users[self.user_name][1]= None
			self.broadcastMessage("* user has left the room: {}".format(self.user_name), current_room)
		else:
			self.sendToClient("You're not in a room. Use /join <room-name> to join a room.")

	def getRoom(self,user):
		return self.users[user][1]