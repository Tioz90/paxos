import helper as hp
import sys
import json
import logging
import argparse

# parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("id", type=int)
ap.add_argument("-d", "--debug")
args = vars(ap.parse_args())

# set debug level
if args["debug"] is not None:
	logging.basicConfig(level=args["debug"].upper())
logging.getLogger('apscheduler').setLevel(logging.WARNING)


class Acceptor():

	def __init__(self):

		self.switch_handler = {
			"PROPOSAL": None,
			"PHASE1A":  self.handle_1a,
			"PHASE1B":  None,
			"PHASE2A":  self.handle_2a,
			"PHASE2B":  None,
			"DECISION": None
		}

		self.role = "acceptors"
		self.id = args["id"]
		self.rnd = 0
		self.v_rnd = 0
		self.v_val = None

		self.readSock, self.multicast_group, self.writeSock = hp.init(self.role)


	def handle_1a(self, msg_1a):

		logging.debug("Acceptor {} \n\tReceived message 1A from Proposer {} c_rnd={}".format(self.id, msg_1a["sender_id"], msg_1a["c_rnd"]))

		if msg_1a["c_rnd"] > self.rnd:
			self.rnd = msg_1a["c_rnd"]

			msg_1b = hp.create_message(sender_id=self.id, phase="PHASE1B", rnd=self.rnd, v_rnd=self.v_rnd, v_val=self.v_val)
			self.writeSock.sendto(msg_1b, hp.send_to_role("proposers"))

			logging.debug("Acceptor {} \n\tSent message 1B to Proposer {} rnd={} v_rnd={} v_val={}".format(self.id, msg_1a["sender_id"], self.rnd,
			                                                                                          self.v_rnd, self.v_val))

		return


	def handle_2a(self, msg_2a):

		logging.debug("Acceptor {} \n\tReceived message 2A from Proposer {} c_rnd={} c_val={}".format(self.id, msg_2a["sender_id"], msg_2a["c_rnd"], msg_2a["c_val"]))

		# discard old proposals
		if msg_2a["c_rnd"] < self.rnd:
			return

		self.v_rnd = msg_2a["c_rnd"]
		self.v_val = msg_2a["c_val"]

		msg_2b = hp.create_message(sender_id=self.id, phase="PHASE2B", v_rnd=self.v_rnd, v_val=self.v_val)
		self.writeSock.sendto(msg_2b, hp.send_to_role("proposers"))

		logging.debug("Acceptor {} \n\tSent message 2B to Proposer {} v_rnd={} v_val={}".format(self.id, msg_2a["sender_id"], self.v_rnd, self.v_val))

		return


	def run(self):

		logging.debug("I'm {} and my address is ({})".format(self.role, self.multicast_group))

		while True:

			# logging.debug("Acceptor {} \n\tWaiting for message".format(self.id))

			data, _ = self.readSock.recvfrom(1024)
			msg = hp.read_message(data)
			self.switch_handler[msg["phase"]](msg)


if __name__ == "__main__":

	acceptor = Acceptor()
	acceptor.run()