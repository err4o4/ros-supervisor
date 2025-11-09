#!/usr/bin/env python

import rospy
from ros_supervisor_lib import NodesManager, RecorderManager, SystemMonitor
from ros_supervisor_lib.command_handler import CommandHandler
from ros_supervisor_lib.status_publisher import StatusPublisher
from ros_supervisor.srv import Command


class SupervisorNode:
    """Main supervisor node with unified command and status interfaces"""

    def __init__(self):
        rospy.init_node('supervisor_node')

        # Initialize managers
        self.nodes_manager = NodesManager()
        self.recorder_manager = RecorderManager(data_folder='/root/data')
        self.system_monitor = SystemMonitor()

        # Initialize unified handler and publisher
        self.command_handler = CommandHandler(self.nodes_manager, self.recorder_manager)
        self.status_publisher = StatusPublisher(
            self.nodes_manager,
            self.recorder_manager,
            self.system_monitor
        )

        # Register unified command service
        self.command_srv = rospy.Service(
            '/supervisor/command',
            Command,
            self.command_handler.handle_command
        )

        rospy.loginfo("Supervisor node started with unified interfaces")

    def run(self):
        """Main loop - publish unified status every second"""
        rate = rospy.Rate(1)  # 1 Hz
        while not rospy.is_shutdown():
            # Publish unified supervisor status
            self.status_publisher.publish_status()

            rate.sleep()


if __name__ == '__main__':
    try:
        node = SupervisorNode()
        node.run()
    except rospy.ROSInterruptException:
        pass
