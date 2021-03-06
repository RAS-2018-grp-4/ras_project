#!/usr/bin/env python

import numpy as np
import math
import matplotlib.pyplot as plt
import rospy
import std_msgs.msg
import geometry_msgs.msg
from nav_msgs.msg import Odometry
import itertools
import tf

D = 0.15  # look-ahead distance
L = 0.21  # 24 before
show_animation = True

x_odom = 0.0
y_odom = 0.0
theta_odom = 0.0

#####################################################
#             /left_motor/encoder Callback          #
#####################################################
def odomCallback(msg):
    global x_odom, y_odom, theta_odom
    x_odom = msg.pose.pose.position.x
    y_odom = msg.pose.pose.position.y
    (r, p, y) = tf.transformations.euler_from_quaternion([msg.pose.pose.orientation.x, msg.pose.pose.orientation.y, msg.pose.pose.orientation.z, msg.pose.pose.orientation.w])
    theta_odom = y

#####################################################
#               Initialize Publisher                #
#####################################################
rospy.init_node('path_follower_node', anonymous=True)
pub_path_following_VEL = rospy.Publisher('/keyboard/vel', geometry_msgs.msg.Twist, queue_size=1)
rate = rospy.Rate(50)

# odom subscriber
rospy.Subscriber("/robot_odom", Odometry, odomCallback)

class State:
    def __init__(self, x=0.0, y=0.0, yaw=0.0):
        self.x = x
	self.y = y
	self.yaw = yaw

def send_message(LINEAR_VELOCITY, ANGULAR_VELOCITY):
    	VEL = geometry_msgs.msg.Twist()
	
    	if not rospy.is_shutdown():
		VEL.linear.x = LINEAR_VELOCITY
        	VEL.linear.y = 0.0
        	VEL.linear.z = 0.0
        	VEL.angular.x = 0.0
        	VEL.angular.y = 0.0
        	VEL.angular.z = ANGULAR_VELOCITY

        	pub_path_following_VEL.publish(VEL)


def pure_pursuit_control(state, path_x, path_y, t_ind_prev):
    t_ind = calc_target_index(state, path_x, path_y)

    # if the previous target was further away on the path than now, use that instead
    if t_ind_prev >= t_ind:
        t_ind = t_ind_prev

    # target index to coordinates
    if t_ind < len(path_x):
        tx = path_x[t_ind]
        ty = path_y[t_ind]
    else:
        tx = path_x[-1]
        ty = path_y[-1]
        t_ind = len(path_x) - 1

    # calculate the angle to the target point (relative to heading angle)
    alpha = math.atan2(ty - state.y, tx - state.x) - state.yaw

    # if reversing, flip the steering angle
    #if state.v < 0:
    #    alpha = math.pi - alpha

    D_tot = D

    # calculate an appropriate steering angle
    delta = math.atan2(2.0 * L * math.sin(alpha) / D_tot, 1.0)
    return delta, t_ind


def calc_target_index(state, path_x, path_y):
    # find the index of the path closest to the robot
    #print("x,y", state.x,state.y)
 
    dx = [state.x - icx for icx in path_x]
    dy = [state.y - icy for icy in path_y]
    d = [abs(math.sqrt(idx ** 2 + idy ** 2)) for (idx, idy) in zip(dx, dy)]
    t_ind = d.index(min(d))

    # total look ahead distance (taking the speed into consideration)
    D_tot = D

    # search length
    L = 0.0

    # find the index of the look head point on the path (look ahead is the distance ALONG the path, not straight line)
    path_length = len(path_x)
    while L < D_tot and (t_ind + 1) < path_length:
        dx = path_x[t_ind + 1] - path_x[t_ind]
        dy = path_y[t_ind + 1] - path_y[t_ind]
        L += math.sqrt(dx**2 + dy**2)
        t_ind += 1

    return t_ind

def main():
    state = State(x=0,y=0,yaw=0)
    #  target course
    #path_x = np.arange(0, 3, 0.01)
    #path_y = [0.5*math.cos(ix / 0.3)-0.5 for ix in path_x]
    
    path_x1 = np.arange(0, 1, 0.01)
    path_x2 = np.empty(100)
    path_x2.fill(1)
    path_y1 = np.empty(100)
    path_y1.fill(0)
    path_y2 = np.arange(0, 1, 0.01)
    
    path_x = np.append(path_x1, path_x2) 
    path_y = np.append(path_y1, path_y2) 
    print(path_x)
    print(path_y)
    print(len(path_x))
    print(len(path_y))
   

    lastIndex = len(path_x) - 1
    x = [0]
    y = [0]
    yaw = [0]
    t = [0.0]
    state.x = x_odom
    state.y = y_odom
    state.yaw = theta_odom
    target_ind = calc_target_index(state, path_x, path_y)

    while lastIndex > target_ind:
    	state.x = x_odom
    	state.y = y_odom
    	state.yaw = theta_odom

        ang_vel, target_ind = pure_pursuit_control(state, path_x, path_y, target_ind)

	GAIN = 0.7
	lin_vel = 0.07
	send_message(lin_vel, ang_vel*GAIN)
	#rate.sleep()
	print("ang_vel", ang_vel*GAIN)

        x.append(x_odom)
        y.append(y_odom)
        yaw.append(theta_odom)


        if show_animation:
            plt.cla()
            plt.plot(path_x, path_y, ".r", label="course")
            plt.plot([x_odom, x_odom + math.cos(theta_odom)], [y_odom, y_odom + math.sin(theta_odom)], "g", label="angle")
            plt.plot(x, y, "-b", label="trajectory")
            plt.plot(path_x[target_ind], path_y[target_ind], "xg", label="target")
            plt.axis("equal")
            plt.grid(True)
            plt.pause(0.001)

    # Test

    send_message(0, 0)

    assert lastIndex >= target_ind, "Cannot goal"

    if show_animation:
        plt.plot(path_x, path_y, ".r", label="course")
        plt.plot(x, y, "-b", label="trajectory")
        plt.legend()
        plt.xlabel("x[m]")
        plt.ylabel("y[m]")
        plt.axis("equal")
        plt.grid(True)
        plt.show()



if __name__ == '__main__':
    print("path tracker started")
    main()
