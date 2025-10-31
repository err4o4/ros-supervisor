# ROS Supervisor

A simple ROS1 node supervisor that monitors and controls ROS nodes.

## Features

1. **Node Monitor** - Publishes list of running nodes with PIDs every second
2. **File Monitor** - Publishes list of files in /root/data folder every second
3. **Start Node Service** - Start new nodes with launch files and parameters
4. **Stop Node Service** - Stop running nodes by name or PID

## Building

```bash
cd <catkin_workspace>
catkin_make
source devel/setup.bash
```

## Running

```bash
roslaunch ros_supervisor supervisor.launch
```

## Usage

### Monitor Nodes

Subscribe to the topic:
```bash
rostopic echo /supervisor/monitor/nodes
```

### Monitor Files

Subscribe to the topic:
```bash
rostopic echo /supervisor/monitor/records
```

This publishes information about all files in `/root/data` including:
- File name
- File size (bytes)
- Created timestamp

### Start a Node

```bash
rosservice call /supervisor/actions/start_node "package: 'ouster_ros'
launch_file: 'driver.launch'
args:
- {key: 'sensor_hostname', value: '192.168.100.2'}"
```

Multiple arguments:
```bash
rosservice call /supervisor/actions/start_node "package: 'ouster_ros'
launch_file: 'driver.launch'
args:
- {key: 'sensor_hostname', value: '192.168.100.2'}
- {key: 'lidar_mode', value: '1024x10'}"
```

### Stop a Node

By node name:
```bash
rosservice call /supervisor/actions/stop_node "node: '/os_node'
pid: 0"
```

By PID:
```bash
rosservice call /supervisor/actions/stop_node "node: ''
pid: 12345"
```
