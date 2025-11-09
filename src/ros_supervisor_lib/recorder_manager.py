import rospy
import subprocess
import os
import signal
import shutil
from datetime import datetime
from ros_supervisor.msg import RecordingFile


class RecorderManager:
    """Manages rosbag recordings - starting, stopping, deleting, and monitoring"""

    def __init__(self, data_folder='/root/data'):
        # Data folder path
        self.data_folder = data_folder

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
                        file_record = RecordingFile()
                        file_record.name = filename
                        file_record.size_bytes = stat.st_size
                        file_record.created = rospy.Time.from_sec(stat.st_ctime)
                        files.append(file_record)
        except Exception as e:
            rospy.logwarn(f"Error reading data folder: {e}")
        return files

    def is_recording(self):
        """Check if currently recording"""
        return self.recording_process is not None and self.recording_process.poll() is None
