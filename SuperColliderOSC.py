import liblo

class SuperColliderClient:
    '''Class to send OSC messages to SC server'''
    def __init__(self):
        self.osctarget = liblo.Address("127.0.0.1", 57110)
        self.liblo_time_diff = 2208988800.0

    def sc_bundle(self, timetag, msgAdr="/s_new", msgArgs=["s1", 2000, 1, 0, "freq", 300, "amp", 0.5]):
        '''A bundle includes a time tag'''
        global client
        message = liblo.Message(msgAdr)
        for arg in msgArgs:
            message.add(arg)
        bundle = liblo.Bundle(timetag+self.liblo_time_diff, message)
        liblo.send(self.osctarget, bundle)

    def sc_msg(self, msgAdr="/s_new", msgArgs=["s1", 2000, 1, 0, "freq", 300, "amp", 0.5]):
        message = liblo.Message(msgAdr)
        for arg in msgArgs:
            message.add(arg)
        liblo.send(self.osctarget, message)

class OSCsend_receive:
    '''Class to communicate to the SC language'''
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.client = liblo.Address(self.host, self.port)
        self.liblo_time_diff = 2208988800.0

    def sc_msg_other(self, msgAdr="/s_new", msgArgs=["s1", 2000, 1, 0, "freq", 300, "amp", 0.5]):
        message = liblo.Message(msgAdr)
        for arg in msgArgs:
            message.add(arg)
        liblo.send(self.client, message)

    def sc_bundle_other(self, timetag, msgAdr="/s_new", msgArgs=["s1", 2000, 1, 0, "freq", 300, "amp", 0.5]):
        message = liblo.Message(msgAdr)
        for arg in msgArgs:
            message.add(arg)
        bundle = liblo.Bundle(timetag+self.liblo_time_diff, message)
        liblo.send(self.client, bundle)