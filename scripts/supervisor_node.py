#!/usr/bin/env python

import rospy
from ros_supervisor_lib import NodesManager, RecorderManager, SystemMonitor
from ros_supervisor.srv import StartNode, StopNode, DeleteRecording, StartRecording, StopRecording


class SupervisorNode:
    """Main supervisor node that coordinates node and recorder management"""

    def __init__(self):
        rospy.init_node('supervisor_node')

        # Initialize managers
        self.nodes_manager = NodesManager()
        self.recorder_manager = RecorderManager(data_folder='/root/data')
        self.system_monitor = SystemMonitor()

        # Register node management services
        self.start_srv = rospy.Service('supervisor/actions/start_node', StartNode, self.nodes_manager.handle_start_node)
        self.stop_srv = rospy.Service('supervisor/actions/stop_node', StopNode, self.nodes_manager.handle_stop_node)

        # Register recording management services
        self.delete_srv = rospy.Service('supervisor/actions/delete_recording', DeleteRecording, self.recorder_manager.handle_delete_recording)
        self.start_rec_srv = rospy.Service('supervisor/actions/start_recording', StartRecording, self.recorder_manager.handle_start_recording)
        self.stop_rec_srv = rospy.Service('supervisor/actions/stop_recording', StopRecording, self.recorder_manager.handle_stop_recording)

        rospy.loginfo("Supervisor node started")

    def run(self):
        """Main loop - publish monitoring data every second"""
        rate = rospy.Rate(1)  # 1 Hz
        while not rospy.is_shutdown():
            # Publish node monitoring data
            self.nodes_manager.publish_nodes()

            # Publish file list
            self.recorder_manager.publish_files()

            # Always publish recording status (includes disk space)
            self.recorder_manager.publish_recording_status()

            # Publish system status (CPU and RAM)
            self.system_monitor.publish_system_status()

            rate.sleep()


if __name__ == '__main__':
    try:
        node = SupervisorNode()
        node.run()
    except rospy.ROSInterruptException:
        pass
