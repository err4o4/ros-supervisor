## ROS Supervisor

A lightweight ROS node management and system monitoring service that gives you remote control over your robot.

Initially designed for [RView](https://github.com/err4o4/rview) to provide a complete web-based control interface for handheld SLAM scanner.

## Features:

- Start/stop/track ROS nodes with launch files and dynamic parameters
- Start/stop/list rosbag recording for selected topics
- Monitor system resources (CPU, RAM, disk usage) in real-time

All management happens through a single service endpoint (`/supervisor/command`) and a consolidated status topic (`/supervisor/status`), making integration simple.

## Running:

```bash
cd <catkin_workspace>/src
git clone https://github.com/err4o4/ros-supervisor.git
cd ..
catkin_make
source devel/setup.bash
roslaunch ros_supervisor supervisor.launch
```

## Status Topic

Subscribe to get everything in one message:

```bash
rostopic echo /supervisor/status
```

This publishes a consolidated `SupervisorStatus` message every second containing:
- **System resources** – CPU usage, RAM usage, disk space
- **Recording status** – active recording filename, duration, file size, topics being recorded
- **Running nodes** – list of all ROS nodes with PIDs
- **Available recordings** – all bag files in data folder with sizes and timestamps
- **Supervisor health** – uptime, version, status

## Command Service

All actions go through a single service:

```bash
rosservice call /supervisor/command
```

### Start a Node

```bash
rosservice call /supervisor/command "action: 'start_node'
params:
  package: 'fast_lio'
  launch_file: 'mapping.launch'
  args:
  - {key: 'config_file', value: 'velodyne.yaml'}"
```

Multiple arguments:
```bash
rosservice call /supervisor/command "action: 'start_node'
params:
  package: 'ouster_ros'
  launch_file: 'driver.launch'
  args:
  - {key: 'sensor_hostname', value: '192.168.100.2'}
  - {key: 'lidar_mode', value: '1024x10'}"
```

### Stop a Node

By node name:
```bash
rosservice call /supervisor/command "action: 'stop_node'
params:
  node: '/os_node'"
```

By PID:
```bash
rosservice call /supervisor/command "action: 'stop_node'
params:
  pid: 12345"
```

### Start Recording

```bash
rosservice call /supervisor/command "action: 'start_recording'
params:
  topics:
  - '/cloud_registered'
  - '/Odometry'
  - '/imu/data'"
```

Recording saves to `/root/data/` with auto-generated timestamp filenames (e.g., `20250314_153042.bag`).

### Stop Recording

```bash
rosservice call /supervisor/command "action: 'stop_recording'"
```

Returns recording metadata (duration, final file size).

### Delete Recording

```bash
rosservice call /supervisor/command "action: 'delete_recording'
params:
  filename: '20250314_153042.bag'"
```

## Configuration

**Data folder:** `/root/data` (hardcoded) — all rosbag recordings are stored here.

**Update rate:** 1Hz status publishing.

**Recording:** Only one active recording at a time. Graceful shutdown with 10-second timeout on stop.

If you're using RView, configure your nodes and recording topics in Rview's `app-config.json` instead of calling services manually.

## Message Definitions

The package defines custom messages for all status and command operations. Key messages:

- `SupervisorStatus.msg` – main unified status message
- `Command.srv` – unified command service
- `SystemResources.msg` – CPU, RAM, storage aggregated status
- `RecordingStatusNew.msg` – current recording state
- `NodesStatus.msg` – running nodes with PIDs
- `RecordingsStatus.msg` – available bag files

Check the `msg/` and `srv/` folders for full definitions.
