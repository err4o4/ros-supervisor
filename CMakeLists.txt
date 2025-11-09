cmake_minimum_required(VERSION 3.0.2)
project(ros_supervisor)

find_package(catkin REQUIRED COMPONENTS
  rospy
  std_msgs
  message_generation
)

add_message_files(
  FILES
  # Base types
  NodeInfo.msg
  KeyValue.msg
  # Nested status messages
  CpuStatus.msg
  RamStatus.msg
  StorageStatus.msg
  SystemResources.msg
  RecordingFile.msg
  RecordingsStatus.msg
  NodesStatus.msg
  SupervisorHealth.msg
  RecordingStatusNew.msg
  # Command messages
  CommandParams.msg
  CommandData.msg
  # Main status message
  SupervisorStatus.msg
)

add_service_files(
  FILES
  Command.srv
)

catkin_python_setup()

generate_messages(
  DEPENDENCIES
  std_msgs
)

catkin_package(
  CATKIN_DEPENDS rospy std_msgs message_runtime
)

catkin_install_python(PROGRAMS
  scripts/supervisor_node.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
