from chat_server import ChatServer
from twisted.internet import reactor

if __name__ == '__main__':
	reactor.listenTCP(9399, ChatServer())
	reactor.run()