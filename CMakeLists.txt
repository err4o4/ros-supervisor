cmake_minimum_required(VERSION 3.0.2)
project(ros_supervisor)

find_package(catkin REQUIRED COMPONENTS
  rospy
  std_msgs
  message_generation
)

add_message_files(
  FILES
  NodeInfo.msg
  NodeList.msg
  KeyValue.msg
  FileRecord.msg
  FileRecordList.msg
  RecordingStatus.msg
  SystemStatus.msg
)

add_service_files(
  FILES
  StartNode.srv
  StopNode.srv
  DeleteRecording.srv
  StartRecording.srv
  StopRecording.srv
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
