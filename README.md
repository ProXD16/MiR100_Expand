# MIR100_WebApp <<Dự án này chỉ chạy được trên Ubuntu>>
- Cần cài đặt: ROS1 (NOETIC hoặc MELODIC), cài đặt package MIR100 từ https://github.com/DFKI-NI/mir_robot, cài đặt Python 3.8.11 và các thư viện về Dash Plotly
  + Cách cài package MIR100: làm theo các bước sau:
        # create a catkin workspace
        mkdir -p ~/catkin_ws/src
        cd ~/catkin_ws/src/
        
        # clone mir_robot into the catkin workspace
        git clone -b noetic https://github.com/DFKI-NI/mir_robot.git
        
        # use rosdep to install all dependencies (including ROS itself)
        sudo apt-get update -qq
        sudo apt-get install -qq -y python-rosdep
        sudo rosdep init
        rosdep update
        rosdep install --from-paths ./ -i -y --rosdistro noetic
        
        # build all packages in the catkin workspace
        source /opt/ros/noetic/setup.bash
        catkin_init_workspace
        cd ~/catkin_ws
        catkin_make -DCMAKE_BUILD_TYPE=RelWithDebugInfo

  + Chạy mô phỏng trên Gazebo và Rviz: Chạy theo từng bước sau
    roslaunch mir_gazebo mir_maze_world.launch
    rosservice call /gazebo/unpause_physics
    roslaunch mir_navigation amcl.launch initial_pose_x:=10.0 initial_pose_y:=10.0
    roslaunch mir_navigation start_planner.launch \
    map_file:=$(rospack find mir_gazebo)/maps/maze.yaml \
    virtual_walls_map_file:=$(rospack find mir_gazebo)/maps/maze_virtual_walls.yaml
    rviz     --> Rồi Mở config new.rviz ở file github cung cấp (Chọn File->New Config)

    Sau khi khởi tạo MIR mô phỏng
    - Chạy file ros_map_listener.py trong folder listener_topic_from_ros để lấy ảnh map
    - Tiếp tắt file ros_map_listener.py rồi chạy file main.py để lấy full thông tin từ ROS
    - Sau đó chạy file app.py để khởi tạo webapp
    - Truy cập đường link sau: http://127.0.0.1:8000/ (Chú ý nhớ đổi IP trong các file và folder app.py, page_map, page_mission, Ở đây đang để mặc định IP là: 192.168.0.172)

  + Chạy Robot MIR100 thực tế:
    - Kết nối máy tính cá nhân với MIR100 thông qua cổng Ethernet (Nếu ở phòng C7-612 sử dụng mạng Tenda.... thì truy cập luôn tới đường link 192.168.0.172)
    - Truy cập trang web mir.com đăng nhập với (user:admin, password:admin)
    - Truy cập phần Setting (Set up) -> Wifi -> Add -> Thêm tên và Wifi muốn sử dụng
    - Refresh lại trang và xem MIR đã kết nối với wifi mong muốn chưa, nếu rồi xem địa chỉ IP bên dưới
    - Kết nối Wifi và xem địa chỉ IP xong rút dây ethernet và truy cập đường link là địa chỉ IP để truy cập tới interface của MIR
    - Mở terminal chạy lệnh sau: roslaunch mir_driver mir.launch mir_hostname:={IP} (Thay địa chỉ IP tìm được ở trên vào nhớ bỏ dấu {} =)))
    - Tiếp chạy Terminal mới và chạy lệnh: rosrun tf tf_monitor để đồng bộ thời gian của MIR với thời gian thực
    - Chạy file main.py sau đó chạy file app.py
    - Truy cập đường link http://127.0.0.1:8000/

    *********************************************************************************
    *********************************************************************************
