import rospy
import rosnode
import psutil
from ros_supervisor.msg import NodeInfo


class NodesManager:
    """Manages ROS nodes - starting, stopping, and monitoring"""

    def __init__(self):
        # Track launched processes
        self.launched_processes = {}

        rospy.loginfo("Nodes manager initialized")

    def get_node_pid(self, node_name):
        """Get PID for a given node name using psutil"""
        try:
            # Extract base name from full node path (e.g., /ouster/os_driver -> os_driver)
            base_name = node_name.split('/')[-1]

            # Search for process with node name in command line
            for proc in psutil.process_iter(['pid', 'cmdline', 'name']):
                try:
                    cmdline = proc.info.get('cmdline')
                    if cmdline:
                        # Check if this is a ROS node with matching name
                        cmdline_str = ' '.join(cmdline)
                        # Check for __name:=base_name (exact match after __name:=)
                        if '__name:=' + base_name in cmdline_str:
                            return proc.info['pid']
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            rospy.logdebug(f"Error getting PID for {node_name}: {e}")
        return None

    def get_all_nodes_with_pids(self):
        """Get list of all running nodes with their PIDs"""
        nodes = []
        try:
            node_names = rosnode.get_node_names()
            for node_name in node_names:
                pid = self.get_node_pid(node_name)
                if pid:
                    nodes.append(NodeInfo(name=node_name, pid=pid))
            # Sort by PID in descending order (highest PID first)
            nodes.sort(key=lambda node: node.pid, reverse=True)
        except Exception as e:
            rospy.logwarn(f"Error getting nodes: {e}")
        return nodes

