import rospy
import psutil
from ros_supervisor.msg import SystemStatus


class SystemMonitor:
    """Monitors system resources - CPU and RAM usage"""

    def __init__(self):
        # Publisher for system monitoring
        self.pub = rospy.Publisher('supervisor/monitor/system', SystemStatus, queue_size=10)

        # CPU count
        self.cpu_count = psutil.cpu_count()

        rospy.loginfo("System monitor initialized")

    def get_system_status(self):
        """Get current system resource usage"""
        # Get CPU usage per core
        # interval=None uses cached value for faster response
        # For first call or when you need fresh data, use interval=0.1
        cpu_percents = psutil.cpu_percent(percpu=True, interval=0.1)
        cpu_avg = sum(cpu_percents) / len(cpu_percents) if cpu_percents else 0.0

        # Get RAM usage
        mem = psutil.virtual_memory()

        return {
            'cpu_count': self.cpu_count,
            'cpu_percent': cpu_percents,
            'cpu_percent_avg': cpu_avg,
            'ram_total': mem.total,
            'ram_used': mem.used,
            'ram_available': mem.available,
            'ram_percent': mem.percent
        }

    def publish_system_status(self):
        """Publish current system status"""
        try:
            status = self.get_system_status()

            msg = SystemStatus()
            msg.stamp = rospy.Time.now()
            msg.cpu_count = status['cpu_count']
            msg.cpu_percent = status['cpu_percent']
            msg.cpu_percent_avg = status['cpu_percent_avg']
            msg.ram_total = status['ram_total']
            msg.ram_used = status['ram_used']
            msg.ram_available = status['ram_available']
            msg.ram_percent = status['ram_percent']

            self.pub.publish(msg)

        except Exception as e:
            rospy.logwarn(f"Error publishing system status: {e}")
