import rospy
import subprocess
import os
import signal
import shutil
from datetime import datetime
from ros_supervisor.msg import FileRecord, FileRecordList, RecordingStatus
from ros_supervisor.srv import DeleteRecordingResponse, StartRecordingResponse, StopRecordingResponse


class RecorderManager:
    """Manages rosbag recordings - starting, stopping, deleting, and monitoring"""

    def __init__(self, data_folder='/root/data'):
        # Data folder path
        self.data_folder = data_folder

        # Publisher for file monitoring
        self.file_pub = rospy.Publisher('supervisor/monitor/records', FileRecordList, queue_size=10)

        # Publisher for recording status
        self.recording_pub = rospy.Publisher('supervisor/monitor/recording', RecordingStatus, queue_size=10)

        # Track recording process
        self.recording_process = None
        self.recording_filename = None
        self.recording_start_time = None
        self.recording_filepath = None

        rospy.loginfo("Recorder manager initialized")

    def get_files_in_data_folder(self):
        """Get list of files in data folder"""
        files = []
        try:
            if os.path.exists(self.data_folder) and os.path.isdir(self.data_folder):
                for filename in os.listdir(self.data_folder):
                    filepath = os.path.join(self.data_folder, filename)
                    if os.path.isfile(filepath):
                        stat = os.stat(filepath)
                        file_record = FileRecord()
                        file_record.name = filename
                        file_record.size = stat.st_size
                        file_record.created = rospy.Time.from_sec(stat.st_ctime)
                        files.append(file_record)
        except Exception as e:
            rospy.logwarn(f"Error reading data folder: {e}")
        return files

    def publish_files(self):
        """Publish current list of files in data folder"""
        files = self.get_files_in_data_folder()
        msg = FileRecordList()
        msg.stamp = rospy.Time.now()
        msg.count = len(files)
        msg.files = files
        self.file_pub.publish(msg)

    def publish_recording_status(self, stopped=False):
        """Publish current recording status"""
        msg = RecordingStatus()
        msg.stamp = rospy.Time.now()

        # Always get disk space
        space_left = 0
        try:
            stat = shutil.disk_usage(self.data_folder)
            space_left = stat.free
        except Exception as e:
            rospy.logdebug(f"Error getting disk space: {e}")

        if stopped or self.recording_process is None:
            # Publish stopped status
            msg.recording = False
            msg.recording_time = rospy.Duration(0)
            msg.filename = ""
            msg.filesize = 0
            msg.space_left = space_left
        else:
            # Calculate recording time
            recording_duration = rospy.Time.now() - self.recording_start_time

            # Get file size if file exists
            filesize = 0
            if self.recording_filepath:
                try:
                    # rosbag creates .bag.active while recording, then renames to .bag when done
                    active_filepath = self.recording_filepath + ".active"
                    if os.path.exists(active_filepath):
                        filesize = os.path.getsize(active_filepath)
                    elif os.path.exists(self.recording_filepath):
                        filesize = os.path.getsize(self.recording_filepath)
                except Exception as e:
                    rospy.logdebug(f"Error getting file size: {e}")

            msg.recording = True
            msg.recording_time = recording_duration
            msg.filename = self.recording_filename or ""
            msg.filesize = filesize
            msg.space_left = space_left

        self.recording_pub.publish(msg)

    def is_recording(self):
        """Check if currently recording"""
        return self.recording_process is not None and self.recording_process.poll() is None

    def handle_start_recording(self, req):
        """Start rosbag recording with specified topics"""
        resp = StartRecordingResponse()

        try:
            # Check if already recording
            if self.is_recording():
                resp.ok = False
                resp.error = "Recording already in progress"
                rospy.logwarn("Attempted to start recording while already recording")
                return resp

            # Validate topics list
            if not req.topics or len(req.topics) == 0:
                resp.ok = False
                resp.error = "No topics specified for recording"
                rospy.logwarn("No topics specified for recording")
                return resp

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}.bag"
            filepath = os.path.join(self.data_folder, filename)

            # Ensure data folder exists
            if not os.path.exists(self.data_folder):
                os.makedirs(self.data_folder)

            # Build rosbag command
            cmd = ['rosbag', 'record', '-O', filepath] + list(req.topics)

            # Start recording process
            rospy.loginfo(f"Starting recording: {' '.join(cmd)}")
            self.recording_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.recording_filename = filename
            self.recording_filepath = filepath
            self.recording_start_time = rospy.Time.now()

            resp.ok = True
            resp.message = f"Recording started to {filename}"
            resp.filename = filename
            rospy.loginfo(f"Recording started: {filename}")

        except Exception as e:
            rospy.logerr(f"Error starting recording: {e}")
            resp.ok = False
            resp.error = str(e)
            self.recording_process = None
            self.recording_filename = None
            self.recording_filepath = None
            self.recording_start_time = None

        return resp

    def handle_stop_recording(self, req):
        """Stop current rosbag recording gracefully"""
        resp = StopRecordingResponse()

        try:
            # Check if recording is in progress
            if self.recording_process is None:
                resp.ok = False
                resp.error = "No recording in progress"
                rospy.logwarn("Attempted to stop recording when none is active")
                return resp

            # Check if process is still running
            if self.recording_process.poll() is not None:
                resp.ok = False
                resp.error = "Recording process already terminated"
                rospy.logwarn("Recording process was already terminated")
                # Publish stopped status before clearing
                self.publish_recording_status(stopped=True)
                self.recording_process = None
                self.recording_filename = None
                self.recording_filepath = None
                self.recording_start_time = None
                return resp

            # Send SIGINT to rosbag process for graceful shutdown
            rospy.loginfo(f"Stopping recording: {self.recording_filename}")
            self.recording_process.send_signal(signal.SIGINT)

            # Wait for process to finish (with timeout)
            try:
                self.recording_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                rospy.logwarn("Recording process did not stop gracefully, terminating...")
                self.recording_process.terminate()
                self.recording_process.wait(timeout=5)

            resp.ok = True
            resp.message = f"Recording stopped: {self.recording_filename}"
            resp.filename = self.recording_filename
            rospy.loginfo(f"Recording stopped: {self.recording_filename}")

            # Publish stopped status before clearing
            self.publish_recording_status(stopped=True)

            # Clear recording state
            self.recording_process = None
            self.recording_filename = None
            self.recording_filepath = None
            self.recording_start_time = None

        except Exception as e:
            rospy.logerr(f"Error stopping recording: {e}")
            resp.ok = False
            resp.error = str(e)

        return resp

    def handle_delete_recording(self, req):
        """Delete a recording file from the data folder"""
        resp = DeleteRecordingResponse()

        try:
            # Validate filename (prevent directory traversal attacks)
            if not req.filename or '..' in req.filename or '/' in req.filename:
                resp.ok = False
                resp.error = "Invalid filename"
                rospy.logwarn(f"Invalid filename requested for deletion: {req.filename}")
                return resp

            # Build full file path
            filepath = os.path.join(self.data_folder, req.filename)

            # Check if file exists
            if not os.path.exists(filepath):
                resp.ok = False
                resp.error = f"File '{req.filename}' not found in {self.data_folder}"
                rospy.logwarn(f"File not found: {filepath}")
                return resp

            # Check if it's actually a file
            if not os.path.isfile(filepath):
                resp.ok = False
                resp.error = f"'{req.filename}' is not a file"
                rospy.logwarn(f"Not a file: {filepath}")
                return resp

            # Delete the file
            os.remove(filepath)
            resp.ok = True
            resp.message = f"File '{req.filename}' deleted successfully"
            rospy.loginfo(f"Deleted file: {filepath}")

        except Exception as e:
            rospy.logerr(f"Error deleting file: {e}")
            resp.ok = False
            resp.error = str(e)

        return resp
