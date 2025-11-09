import rospy
import psutil
import shutil
import os
from ros_supervisor.msg import (
    SupervisorStatus,
    SystemResources, CpuStatus, RamStatus, StorageStatus,
    RecordingStatusNew, NodeInfo,
    NodesStatus, RecordingsStatus, RecordingFile,
    SupervisorHealth
)


class StatusPublisher:
    """Publishes unified supervisor status combining all subsystems"""

    def __init__(self, nodes_manager, recorder_manager, system_monitor):
        self.nodes_manager = nodes_manager
        self.recorder_manager = recorder_manager
        self.system_monitor = system_monitor

        # Publisher for unified status
        self.pub = rospy.Publisher('/supervisor/status', SupervisorStatus, queue_size=10)

        # Track supervisor start time
        self.start_time = rospy.Time.now()
        self.version = "1.0.0"

        rospy.loginfo("Status publisher initialized")

    def publish_status(self):
        """Publish unified supervisor status"""
        try:
            msg = SupervisorStatus()
            msg.stamp = rospy.Time.now()

            # System resources
            msg.system = self._get_system_resources()

            # Recording status
            msg.recording = self._get_recording_status()

            # Running nodes
            msg.nodes = self._get_nodes_status()

            # Available recordings
            msg.recordings = self._get_recordings_status()

            # Supervisor health
            msg.supervisor = self._get_supervisor_health()

            self.pub.publish(msg)

        except Exception as e:
            rospy.logwarn(f"Error publishing unified status: {e}")

    def _get_system_resources(self):
        """Get system resource status"""
        system = SystemResources()

        # CPU status
        cpu_percents = psutil.cpu_percent(percpu=True, interval=0.1)
        cpu_avg = sum(cpu_percents) / len(cpu_percents) if cpu_percents else 0.0

        system.cpu = CpuStatus()
        system.cpu.count = psutil.cpu_count()
        system.cpu.percent_avg = cpu_avg
        system.cpu.percent_per_core = cpu_percents

        # RAM status
        mem = psutil.virtual_memory()
        system.ram = RamStatus()
        system.ram.total_bytes = mem.total
        system.ram.used_bytes = mem.used
        system.ram.available_bytes = mem.available
        system.ram.percent = mem.percent

        # Storage status
        try:
            disk = shutil.disk_usage(self.recorder_manager.data_folder)
            system.storage = StorageStatus()
            system.storage.total_bytes = disk.total
            system.storage.used_bytes = disk.used
            system.storage.available_bytes = disk.free
            system.storage.percent = (disk.used / disk.total * 100) if disk.total > 0 else 0.0
        except Exception as e:
            rospy.logdebug(f"Error getting storage status: {e}")
            system.storage = StorageStatus()
            system.storage.total_bytes = 0
            system.storage.used_bytes = 0
            system.storage.available_bytes = 0
            system.storage.percent = 0.0

        return system

    def _get_recording_status(self):
        """Get current recording status"""
        recording = RecordingStatusNew()

        if self.recorder_manager.recording_process is None or \
           self.recorder_manager.recording_process.poll() is not None:
            # Not recording
            recording.is_recording = False
            recording.filename = ""
            recording.recording_time = rospy.Duration(0)
            recording.size_bytes = 0
            recording.topics = []
        else:
            # Currently recording
            recording.is_recording = True
            recording.filename = self.recorder_manager.recording_filename or ""

            # Calculate recording time
            if self.recorder_manager.recording_start_time:
                elapsed = rospy.Time.now() - self.recorder_manager.recording_start_time
                recording.recording_time = rospy.Duration(elapsed.to_sec())
            else:
                recording.recording_time = rospy.Duration(0)

            # Get file size
            # Note: rosbag creates .bag.active while recording, then renames to .bag when done
            try:
                if self.recorder_manager.recording_filepath:
                    active_filepath = self.recorder_manager.recording_filepath + ".active"
                    if os.path.exists(active_filepath):
                        recording.size_bytes = os.path.getsize(active_filepath)
                    elif os.path.exists(self.recorder_manager.recording_filepath):
                        recording.size_bytes = os.path.getsize(self.recorder_manager.recording_filepath)
                    else:
                        recording.size_bytes = 0
                else:
                    recording.size_bytes = 0
            except Exception as e:
                rospy.logdebug(f"Error getting recording file size: {e}")
                recording.size_bytes = 0

            # Topics (we don't store this currently, so leave empty)
            recording.topics = []

        return recording

    def _get_nodes_status(self):
        """Get running nodes status"""
        nodes_status = NodesStatus()

        nodes_list = self.nodes_manager.get_all_nodes_with_pids()
        nodes_status.count = len(nodes_list)
        nodes_status.list = nodes_list

        return nodes_status

    def _get_recordings_status(self):
        """Get available recordings status"""
        recordings_status = RecordingsStatus()

        files = self.recorder_manager.get_files_in_data_folder()

        # Convert from FileRecord to RecordingFile format
        recording_files = []
        total_size = 0
        for file in files:
            rec_file = RecordingFile()
            rec_file.name = file.name
            rec_file.size_bytes = file.size
            rec_file.created = file.created
            recording_files.append(rec_file)
            total_size += file.size

        recordings_status.count = len(recording_files)
        recordings_status.total_size_bytes = total_size
        recordings_status.list = recording_files

        return recordings_status

    def _get_supervisor_health(self):
        """Get supervisor health status"""
        health = SupervisorHealth()

        # Calculate uptime
        uptime_secs = (rospy.Time.now() - self.start_time).to_sec()
        health.uptime = rospy.Duration(uptime_secs)

        health.version = self.version
        health.healthy = True  # Could add more sophisticated health checks

        return health
