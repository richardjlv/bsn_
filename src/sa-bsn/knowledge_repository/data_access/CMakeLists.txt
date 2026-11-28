CMAKE_MINIMUM_REQUIRED (VERSION 2.8.3)
PROJECT(repository)

add_compile_options(-std=c++11)

###########################################################################
## Find catkin and any catkin packages
FIND_PACKAGE(catkin REQUIRED COMPONENTS roscpp std_msgs genmsg roslib messages archlib lepton libbsn)

###########################################################################
# Export catkin package.
CATKIN_PACKAGE(
    INCLUDE_DIRS include
    LIBRARIES ${PROJECT_NAME}
    CATKIN_DEPENDS messages message_runtime archlib lepton libbsn
)

###########################################################################
# Set catkin directory.
INCLUDE_DIRECTORIES(${catkin_INCLUDE_DIRS})

# Set include directory.
INCLUDE_DIRECTORIES(include)

###########################################################################
# Build this project.
FILE(GLOB ${PROJECT_NAME}-src "${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp")

SET(data_access-src "${CMAKE_CURRENT_SOURCE_DIR}/src/DataAccess.cpp")
ADD_EXECUTABLE (data_access  "${CMAKE_CURRENT_SOURCE_DIR}/apps/data_access.cpp" ${${PROJECT_NAME}-src} ${data_access-src})
TARGET_LINK_LIBRARIES (data_access PRIVATE ${catkin_LIBRARIES} ${LIBRARIES})
ADD_DEPENDENCIES(data_access messages_generate_messages_cpp)

###########################################################################
# Tests.
if(CATKIN_ENABLE_TESTING)
  find_package(ros_pytest QUIET)
  if(ros_pytest_FOUND)
    find_package(rostest REQUIRED)

    add_rostest(test/unit/test_data_access.launch
      ARGS "test_pythonpath:=${CATKIN_DEVEL_PREFIX}/${CATKIN_GLOBAL_PYTHON_DESTINATION}")
  else()
    message(STATUS "ros_pytest absent: skipping Python ROS tests; see README.md")
  endif()
endif()
