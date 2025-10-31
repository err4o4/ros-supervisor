import rospy
import rosnode
import subprocess
import psutil
import os
import signal
from ros_supervisor.msg import NodeInfo, NodeList
from ros_supervisor.srv import StartNodeResponse, StopNodeResponse


class NodesManager:
    """Manages ROS nodes - starting, stopping, and monitoring"""

    def __init__(self):
        # Publisher for node monitoring
        self.pub = rospy.Publisher('supervisor/monitor/nodes', NodeList, queue_size=10)

        # Track launched processes
        self.launched_processes = {}

        rospy.loginfo("Nodes manager initialized")

    def get_node_pid(self, node_name):
        """Get PID for a given node name using psutil"""
        try:
            # Search for process with node name in command line
            for proc in psutil.process_iter(['pid', 'cmdline', 'name']):
                try:
                    cmdline = proc.info.get('cmdline')
                    if cmdline:
                        # Check if this is a ROS node with matching name
                        cmdline_str = ' '.join(cmdline)
                        if '__name:=' + node_name in cmdline_str or node_name in cmdline_str:
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
        except Exception as e:
            rospy.logwarn(f"Error getting nodes: {e}")
        return nodes

    def publish_nodes(self):
        """Publish current list of nodes"""
        nodes = self.get_all_nodes_with_pids()
        msg = NodeList()
        msg.stamp = rospy.Time.now()
        msg.count = len(nodes)
        msg.nodes = nodes
        self.pub.publish(msg)

    def handle_start_node(self, req):
        """Start a new node with roslaunch"""
        resp = StartNodeResponse()
        try:
            # Build roslaunch command
            cmd = ['roslaunch', req.package, req.launch_file]

            # Add arguments if provided
            for arg in req.args:
                cmd.append(f"{arg.key}:={arg.value}")

            # Launch process
            rospy.loginfo(f"Starting: {' '.join(cmd)}")
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Store process
            self.launched_processes[process.pid] = process

            # Wait a bit for nodes to start
            rospy.sleep(2.0)

            # Get newly started nodes
            nodes = self.get_all_nodes_with_pids()

            resp.ok = True
            resp.roslaunch_pid = process.pid
            resp.nodes = nodes

            rospy.loginfo(f"Successfully started roslaunch with PID {process.pid}")

        except Exception as e:
            rospy.logerr(f"Failed to start node: {e}")
            resp.ok = False

        return resp

    def handle_stop_node(self, req):
        """Stop a running node by name or PID"""
        resp = StopNodeResponse()

        try:
            if req.node:
                # Stop by node name
                rospy.loginfo(f"Stopping node by name: {req.node}")
                try:
                    rosnode.kill_nodes([req.node])
                    resp.ok = True
                    resp.message = f"Node {req.node} stopped"
                except Exception as e:
                    resp.ok = False
                    resp.error = str(e)

            elif req.pid > 0:
                # Stop by PID
                rospy.loginfo(f"Stopping process by PID: {req.pid}")
                try:
                    # Check if this is a roslaunch process we started
                    if req.pid in self.launched_processes:
                        process = self.launched_processes[req.pid]
                        process.terminate()
                        process.wait(timeout=5)
                        del self.launched_processes[req.pid]
                    else:
                        # Try to kill the process directly
                        os.kill(req.pid, signal.SIGTERM)

                    resp.ok = True
                    resp.message = f"Process {req.pid} stopped"
                except Exception as e:
                    resp.ok = False
                    resp.error = str(e)
            else:
                resp.ok = False
                resp.error = "Must specify either node name or pid"

        except Exception as e:
            rospy.logerr(f"Error stopping node: {e}")
            resp.ok = False
            resp.error = str(e)

        return resp
