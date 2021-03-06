import PaxosHelper as hp
import logging
import argparse

# parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("id", type=int)
ap.add_argument("conf", type=str)
ap.add_argument("-d", "--debug")
args = vars(ap.parse_args())

# set debug level
if args["debug"] is not None:
	logging.basicConfig(level=args["debug"].upper())
logging.getLogger('apscheduler').setLevel(logging.WARNING)


class Acceptor():

	def __init__(self):

		self.switch_handler = {
			"PHASE1A":  self.handle_1a,
			"PHASE2A":  self.handle_2a,
			"INSTANCEREQ": self.handle_instancereq
		}

		self.role = "acceptors"
		self.id = args["id"]

		self.state = {}

		self.greatest_instance = -1

		self.readSock, self.multicast_group, self.writeSock = hp.init(self.role, args["conf"])

	# reply to an instance request y a Proposer by sending the greatest instance number seen
	def handle_instancereq(self, msg_instancereq):

		logging.debug(f"Acceptor {self.id} \n\tReceived message INSTANCEREQ from Proposer {msg_instancereq.sender_id}")

		msg_instancerepl = hp.Message.create_instancerepl(self.greatest_instance, self.id)
		self.writeSock.sendto(msg_instancerepl, hp.send_to_role("proposers"))

		logging.debug(f"Acceptor {self.id} \n\tSent message INSTANCEREPL to Proposer {msg_instancereq.sender_id} with instance {self.greatest_instance}")

		return

	def handle_1a(self, msg_1a):

		logging.debug("Acceptor {}, Instance {}\n\tReceived message 1A from Proposer {} c_rnd={}".format(self.id,
		                                                                                                 msg_1a.instance_num,
		                                                                                                 msg_1a.sender_id,
		                                                                                                 msg_1a.c_rnd))

		instance = msg_1a.instance_num

		if instance > self.greatest_instance:
			self.greatest_instance = instance

		if not instance in self.state: # check if instance already exists
			# start logging new instance
			self.state[instance] = hp.Instance(instance, self.id)

		instance_state = self.state[instance]

		if msg_1a.c_rnd > instance_state.rnd:
			instance_state.rnd = msg_1a.c_rnd

			msg_1b = hp.Message.create_1b(instance, self.id, instance_state.rnd, instance_state.v_rnd, instance_state.v_val)
			self.writeSock.sendto(msg_1b, hp.send_to_role("proposers"))

			logging.debug("Acceptor {}, Instance {}\n\tSent message 1B to Proposer {} rnd={} v_rnd={} v_val={}".format(self.id, instance, msg_1a.sender_id, instance_state.rnd, instance_state.v_rnd, instance_state.v_val))

		return

	def handle_2a(self, msg_2a):

		logging.debug("Acceptor {}, Instance {} \n\tReceived message 2A from Proposer {} c_rnd={} c_val={}".format(self.id, msg_2a.instance_num, msg_2a.sender_id, msg_2a.c_rnd, msg_2a.c_val))

		instance = msg_2a.instance_num
		instance_state = self.state[instance]

		if instance > self.greatest_instance:
			self.greatest_instance = instance

		# discard old proposals
		if msg_2a.c_rnd >= instance_state.rnd:
			instance_state.v_rnd = msg_2a.c_rnd
			instance_state.v_val = msg_2a.c_val

			msg_2b = hp.Message.create_2b(instance, self.id, instance_state.v_rnd, instance_state.v_val)
			self.writeSock.sendto(msg_2b, hp.send_to_role("proposers"))

			logging.debug("Acceptor {}, Instance {} \n\tSent message 2B to Proposer {} v_rnd={} v_val={}".format(self.id, instance, msg_2a.sender_id, instance_state.v_rnd, instance_state.v_val))

		return

	def run(self):

		logging.debug("I'm {} and my address is ({})".format(self.role, self.multicast_group))

		while True:

			# logging.debug("Acceptor {} \n\tWaiting for message".format(self.id))

			data, _ = self.readSock.recvfrom(65536)
			msg = hp.Message.read_message(data)
			self.switch_handler[msg.phase](msg)


if __name__ == "__main__":

	acceptor = Acceptor()
	acceptor.run()