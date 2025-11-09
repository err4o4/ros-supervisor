import rospy
from ros_supervisor.srv import CommandResponse
from ros_supervisor.msg import CommandData, NodeInfo


class CommandHandler:
    """Handles unified command routing to appropriate managers"""

    def __init__(self, nodes_manager, recorder_manager):
        self.nodes_manager = nodes_manager
        self.recorder_manager = recorder_manager
        rospy.loginfo("Command handler initialized")

    def handle_command(self, req):
        """Route command to appropriate handler based on action"""
        resp = CommandResponse()
        resp.data = CommandData()  # Initialize empty data

        action = req.action.lower()

        try:
            if action == "start_node":
                return self._handle_start_node(req.params)
            elif action == "stop_node":
                return self._handle_stop_node(req.params)
            elif action == "start_recording":
                return self._handle_start_recording(req.params)
            elif action == "stop_recording":
                return self._handle_stop_recording(req.params)
            elif action == "delete_recording":
                return self._handle_delete_recording(req.params)
            else:
                resp.ok = False
                resp.message = f"Unknown action: {action}"
                rospy.logwarn(f"Unknown command action: {action}")
                return resp

        except Exception as e:
            rospy.logerr(f"Error handling command {action}: {e}")
            resp.ok = False
            resp.message = f"Error: {str(e)}"
            return resp

    def _handle_start_node(self, params):
        """Handle start_node action"""
        resp = CommandResponse()
        resp.data = CommandData()

        try:
            # Validate params
            if not params.package or not params.launch_file:
                resp.ok = False
                resp.message = "Missing required parameters: package and launch_file"
                return resp

            # Build roslaunch command
            cmd = ['roslaunch', params.package, params.launch_file]
            for arg in params.args:
                cmd.append(f"{arg.key}:={arg.value}")

            # Start node using nodes manager
            import subprocess
            rospy.loginfo(f"Starting: {' '.join(cmd)}")
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Store process
            self.nodes_manager.launched_processes[process.pid] = process

            # Wait for nodes to start
            rospy.sleep(2.0)

            # Get newly started nodes
            nodes = self.nodes_manager.get_all_nodes_with_pids()

            resp.ok = True
            resp.message = f"Successfully started roslaunch with PID {process.pid}"
            resp.data.roslaunch_pid = process.pid
            resp.data.started_nodes = nodes

        except Exception as e:
            rospy.logerr(f"Failed to start node: {e}")
            resp.ok = False
            resp.message = f"Failed to start node: {str(e)}"

        return resp

    def _handle_stop_node(self, params):
        """Handle stop_node action"""
        resp = CommandResponse()
        resp.data = CommandData()

        try:
            import rosnode
            import os
            import signal

            if params.node:
                # Stop by node name
                rospy.loginfo(f"Stopping node by name: {params.node}")
                rosnode.kill_nodes([params.node])
                resp.ok = True
                resp.message = f"Node {params.node} stopped"

            elif params.pid > 0:
                # Stop by PID
                rospy.loginfo(f"Stopping process by PID: {params.pid}")
                if params.pid in self.nodes_manager.launched_processes:
                    process = self.nodes_manager.launched_processes[params.pid]
                    process.terminate()
                    process.wait(timeout=5)
                    del self.nodes_manager.launched_processes[params.pid]
                else:
                    os.kill(params.pid, signal.SIGTERM)

                resp.ok = True
                resp.message = f"Process {params.pid} stopped"
            else:
                resp.ok = False
                resp.message = "Must specify either node name or pid"

        except Exception as e:
            rospy.logerr(f"Error stopping node: {e}")
            resp.ok = False
            resp.message = f"Error stopping node: {str(e)}"

        return resp

    def _handle_start_recording(self, params):
        """Handle start_recording action"""
        resp = CommandResponse()
        resp.data = CommandData()

        try:
            # Check if already recording
            if self.recorder_manager.is_recording():
                resp.ok = False
                resp.message = "Recording already in progress"
                return resp

            # Validate topics list
            if not params.topics or len(params.topics) == 0:
                resp.ok = False
                resp.message = "No topics specified for recording"
                return resp

            # Generate filename with timestamp
            from datetime import datetime
            import os
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}.bag"
            filepath = os.path.join(self.recorder_manager.data_folder, filename)

            # Ensure data folder exists
            if not os.path.exists(self.recorder_manager.data_folder):
                os.makedirs(self.recorder_manager.data_folder)

            # Build rosbag command
            import subprocess
            cmd = ['rosbag', 'record', '-O', filepath] + list(params.topics)

            # Start recording process
            rospy.loginfo(f"Starting recording: {' '.join(cmd)}")
            self.recorder_manager.recording_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            self.recorder_manager.recording_filename = filename
            self.recorder_manager.recording_filepath = filepath
            self.recorder_manager.recording_start_time = rospy.Time.now()

            resp.ok = True
            resp.message = f"Recording started to {filename}"
            resp.data.recording_filename = filename

        except Exception as e:
            rospy.logerr(f"Error starting recording: {e}")
            resp.ok = False
            resp.message = f"Error starting recording: {str(e)}"
            self.recorder_manager.recording_process = None
            self.recorder_manager.recording_filename = None
            self.recorder_manager.recording_filepath = None
            self.recorder_manager.recording_start_time = None

        return resp

    def _handle_stop_recording(self, params):
        """Handle stop_recording action"""
        resp = CommandResponse()
        resp.data = CommandData()

        try:
            # Check if recording is in progress
            if self.recorder_manager.recording_process is None:
                resp.ok = False
                resp.message = "No recording in progress"
                return resp

            # Check if process is still running
            if self.recorder_manager.recording_process.poll() is not None:
                resp.ok = False
                resp.message = "Recording process already terminated"
                self.recorder_manager.publish_recording_status(stopped=True)
                self.recorder_manager.recording_process = None
                self.recorder_manager.recording_filename = None
                self.recorder_manager.recording_filepath = None
                self.recorder_manager.recording_start_time = None
                return resp

            # Send SIGINT to rosbag process for graceful shutdown
            import signal
            import subprocess
            rospy.loginfo(f"Stopping recording: {self.recorder_manager.recording_filename}")
            self.recorder_manager.recording_process.send_signal(signal.SIGINT)

            # Wait for process to finish (with timeout)
            try:
                self.recorder_manager.recording_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                rospy.logwarn("Recording process did not stop gracefully, terminating...")
                self.recorder_manager.recording_process.terminate()
                self.recorder_manager.recording_process.wait(timeout=5)

            # Calculate duration
            if self.recorder_manager.recording_start_time:
                duration = (rospy.Time.now() - self.recorder_manager.recording_start_time).to_sec()
            else:
                duration = 0.0

            # Get file size
            import os
            size_bytes = 0
            if os.path.exists(self.recorder_manager.recording_filepath):
                size_bytes = os.path.getsize(self.recorder_manager.recording_filepath)

            resp.ok = True
            resp.message = f"Recording stopped: {self.recorder_manager.recording_filename}"
            resp.data.recording_filename = self.recorder_manager.recording_filename
            resp.data.recording_duration = duration
            resp.data.recording_size_bytes = size_bytes

            rospy.loginfo(f"Recording stopped: {self.recorder_manager.recording_filename}")

            # Publish stopped status before clearing
            self.recorder_manager.publish_recording_status(stopped=True)

            # Clear recording state
            self.recorder_manager.recording_process = None
            self.recorder_manager.recording_filename = None
            self.recorder_manager.recording_filepath = None
            self.recorder_manager.recording_start_time = None

        except Exception as e:
            rospy.logerr(f"Error stopping recording: {e}")
            resp.ok = False
            resp.message = f"Error stopping recording: {str(e)}"

        return resp

    def _handle_delete_recording(self, params):
        """Handle delete_recording action"""
        resp = CommandResponse()
        resp.data = CommandData()

        try:
            # Validate filename (prevent directory traversal attacks)
            if not params.filename or '..' in params.filename or '/' in params.filename:
                resp.ok = False
                resp.message = "Invalid filename"
                return resp

            # Build full file path
            import os
            filepath = os.path.join(self.recorder_manager.data_folder, params.filename)

            # Check if file exists
            if not os.path.exists(filepath):
                resp.ok = False
                resp.message = f"File '{params.filename}' not found"
                return resp

            # Check if it's actually a file
            if not os.path.isfile(filepath):
                resp.ok = False
                resp.message = f"'{params.filename}' is not a file"
                return resp

            # Delete the file
            os.remove(filepath)
            resp.ok = True
            resp.message = f"File '{params.filename}' deleted successfully"
            rospy.loginfo(f"Deleted file: {filepath}")

        except Exception as e:
            rospy.logerr(f"Error deleting file: {e}")
            resp.ok = False
            resp.message = f"Error deleting file: {str(e)}"

        return resp
