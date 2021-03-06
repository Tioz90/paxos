from Paxos_v3 import helper as hp
import logging
import argparse
from apscheduler.schedulers.background import BackgroundScheduler
import time

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


class Learner:

	def __init__(self):

		self.switch_handler = {
			"DECISION": self.handle_decision
		}

		self.role = "learners"
		self.id = args["id"]

		self.decision_dict = {}
		self.last_received = 0
		self.next_deliver = 0
		self.max_received = 0

		self.readSock, self.multicast_group, self.writeSock = hp.init(self.role, args["conf"])

	# TODO se si trova istanza con decisione None, ignorarla perchè non è stata decisa


	def deliver(self):

		for next_decision in sorted(self.decision_dict.keys()):
			# decide on value if it's the next one I'm expecting
			if next_decision == self.next_deliver:
				self.next_deliver += 1

				if self.decision_dict[next_decision].v_val is not None:
					if args["debug"] is None:
						print(self.decision_dict[next_decision].v_val)
					else:
						logging.debug("Learner {} \n\tInstance {}, decided {}".format(self.id,
						                                                              next_decision,
						                                                              self.decision_dict[
							                                                              next_decision].v_val))

	#################################################################
	# Begin catchup values
	#################################################################

	def catchup_request(self, catchup_instance):


		logging.debug("Time {}\tLearner {} \n\tSending CATCHUPREQ for instance {}".format(int(time.time()), self.id,
		                                                                                  catchup_instance))

		msg_catchupreq = hp.Message.create_catchuprequest(catchup_instance, self.id)
		self.writeSock.sendto(msg_catchupreq, hp.send_to_role("proposers"))

		return

	def handle_decision(self, msg_dec):

		logging.debug("Learner {}, Instance {} \n\tReceived DECISION from Proposer {} v_val={}".format(self.id,
		                                                                                               msg_dec.instance_num,
		                                                                                               msg_dec.sender_id,
		                                                                                               msg_dec.v_val))

		self.last_received = msg_dec.instance_num
		self.decision_dict[msg_dec.instance_num] = msg_dec

		self.deliver()

		# nag for missing values every time
		for inst in range(self.next_deliver, self.last_received):
			if not self.instance_is_received(inst):
				self.catchup_request(inst)

	def instance_is_received(self, instance):

		if instance in self.decision_dict:
			return True
		else:
			return False


	def check_all_received(self):

		# logging.debug(f"Learner {self.id} \n\tChecking decisions")

		for inst in self.decision_dict:
			if not self.instance_is_received(inst):
				self.catchup_request(inst)

		self.deliver()

		return

	#################################################################
	# End catchup values
	#################################################################


	def run(self):

		# periodically check if all messages are received and nag if not
		received_sched = BackgroundScheduler()
		received_sched.add_job(self.check_all_received, 'interval', seconds=1)
		received_sched.start()

		logging.debug("I'm {} and my address is ({})".format(self.role, self.multicast_group))

		while True:
			# logging.debug("Learner {} \n\tWaiting for message".format(self.id))

			data, _ = self.readSock.recvfrom(65536)
			msg = hp.Message.read_message(data)
			self.switch_handler[msg.phase](msg)



if __name__ == '__main__':
	learner = Learner()
	learner.run()