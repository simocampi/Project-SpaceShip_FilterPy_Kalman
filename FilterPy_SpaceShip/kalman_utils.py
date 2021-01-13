import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import animation
from matplotlib.animation import FuncAnimation, PillowWriter
import os
from IPython.display import Image, display


from filterpy.kalman import KalmanFilter
from filterpy.common import Q_discrete_white_noise
from scipy.linalg import block_diag
from filterpy.stats import plot_covariance_ellipse
from filterpy.common import Saver



const_acceleration_x = 2
const_acceleration_y = 1
dt=0.001
t= np.arange(0, 1.01, dt)
N = len(t)
traj = (2*(t**5)- 1.5*(t**4) + 0.05*(t**3) - 3*(t**2)+3*t)

t= (t)*100
traj= (traj)*100



def init_global(const_acc_x, const_acc_y,dt_, t_, N_, traj_):
    
    global const_acceleration_x, const_acceleration_y,dt, t, N, traj

    const_acceleration_x, const_acceleration_y = const_acc_x, const_acc_y
    dt, N, traj, t = dt_, N_, traj_, t_




def get_x_y_velocities():
    
    global const_acceleration_x, const_acceleration_y, dt, t, traj


    x_velocities = np.zeros(len(t))
    y_velocities = np.zeros(len(t))
    np.random.seed(25)
    sigma = 0.4
    mu = 0 
    
    for i in range(1,len(t)) :
        
        noise = np.random.normal(loc = mu, scale = sigma)
        
        x_velocities[i] = ( t[i] - (t[i-1]+ (1/2)*const_acceleration_x*dt**2)) + noise
        y_velocities[i] = ( traj[i] - (traj[i-1]+ (1/2)*const_acceleration_y*dt**2)) + noise
    
    return x_velocities, y_velocities


def plot_measurements(measurements,ax):
    
    x_moon, y_moon = measurements.x_pos[len(measurements.x_pos)-1],  measurements.y_pos[len(measurements.y_pos)-1]
    x_earth, y_earth = measurements.x_pos[0], measurements.y_pos[0]
    
    #ax.set( xlim=(-9, np.max(measurements.x_pos)+9), ylim=(-10, np.max(measurements.y_pos)+9 ) )

    plt.figure(figsize=(13,10))
    ax.plot(measurements.x_pos, measurements.y_pos, ls = "--",c='black', label = "Target Trajectoy")
    
    ax.set_title("Target Trajectory", fontsize=15)
    earth = plt.Circle(( x_earth, y_earth), 3, color='blue', label = "Earth")
    moon  = plt.Circle((x_moon, y_moon ), 1.5, color='grey', label = "Moon")
    ax.add_patch(earth)
    ax.add_patch(moon)
    #moon = ax.gca().add_artist(moon)
    #earth = ax.gca().add_artist(earth)
    
    legend_earth = plt.Line2D([0], [0], ls='None', color="blue", marker='o')
    legend_moon = plt.Line2D([0], [0], ls='None', color="grey", marker='o')
    legend_trajectory = plt.Line2D([0], [0], ls='--', color="black")
    ax.legend([legend_earth, legend_moon, legend_trajectory],["Earth","Moon","Target_Trajectory"])


def plot_planets(measurements,ax):
    
    x_moon, y_moon = measurements.x_pos[len(measurements.x_pos)-1],  measurements.y_pos[len(measurements.y_pos)-1]
    x_earth, y_earth = measurements.x_pos[0], measurements.y_pos[0]
    
    earth = plt.Circle(( x_earth, y_earth), 3, color='blue', label = "Earth")
    moon  = plt.Circle((x_moon, y_moon ), 1.5, color='grey', label = "Moon")
    
    ax.add_patch(earth)
    ax.add_patch(moon)

    legend_earth = plt.Line2D([0], [0], ls='None', color="blue", marker='o')
    legend_moon = plt.Line2D([0], [0], ls='None', color="grey", marker='o')

    ax.legend([legend_earth, legend_moon],["Earth","Moon"])


def save_tracking(predictions, measurements, folder_name):
    
    
    plt.figure(figsize=(13,10))
    
    for x,y in zip(predictions[:,0],predictions[:,1]):
        
        plt.clf()
        
        plot_measurements(measurements)
        
        spaceship_pred = plt.Circle(( x, y), 3, color='red', label = "predicted spaceship")
        plt.gca().add_artist(spaceship_pred)
        plt.show()
        


def init_kalman(measurements):
    
    #Transition_Matrix matrix
    PHI =   np.array([[1, 0, dt, 0, (dt**2)/2, 0],
                     [0, 1, 0, dt, 0, (dt**2)/2],
                     [0, 0, 1,  0, dt, 0,],
                     [0, 0, 0,  1, 0, dt],
                     [0, 0, 0,  0,  1 , 0],
                     [0, 0, 0,  0,  0 , 1] ])


    # Matrix Observation_Matrix
    #We are looking for the position of the spaceship
    H = np.array([[1,0,0,0,0,0],
                 [0,1,0,0,0,0]])


    #initial state
    init_states = np.array([measurements.x_pos[0], measurements.y_pos[0], 
                  measurements.x_vel[0], measurements.y_vel[0], const_acceleration_x, const_acceleration_y ])



    acc_noise = (0.01)**2
    G = np.array([ [(dt**2)/2],
                    [(dt**2)/2],
                    [    dt   ],
                    [    dt   ],
                    [    1    ],
                    [    1    ]])

    Q = np.dot(G, G.T)*acc_noise
    
    return init_states, PHI, H, G, Q 



def Ship_tracker(measurements):
    
    global dt

    init_states, PHI, H, G, Q = init_kalman(measurements)
    
    tracker= KalmanFilter(dim_x = 6, dim_z=2)
    tracker.x = init_states

    tracker.F = PHI
    tracker.H = H   # Measurement function
    tracker.P = np.eye(6)*500   # covariance matrix
    tracker.R = np.eye(2)* 0.001  # state uncertainty
    q = Q_discrete_white_noise(2, dt=dt, var=15, block_size=3)
    tracker.Q =  q # process uncertainty
    
    return tracker


def run(tracker, zs):
    
    preds, cov = [],[]
    for z in zs:
        
        tracker.predict()
        tracker.update(z=z)
        
        preds.append(tracker.x)
        cov.append(tracker.P)
    
    return np.array(preds), np.array(cov)


class SpaceAnimation:
    
    """
    :predictions: matrix with the predictions of the states
    :measurements: dataframe with the measurements with noise
    :target_x: target x of the position
    :target_y: target y of the position 
    
    """
    def __init__(self, predictions, measurements, target_x, target_y):
        
        self.x_target = target_x
        self.y_target = target_y

        self.x_pred = predictions[:,0]
        self.y_pred = predictions[:,1]

        self.fig =  plt.figure(figsize=(13,10))
        self.ax = self.fig.add_subplot(1,1,1)
        self.ax.set( xlim=(-9, np.max(self.x_pred)+9), ylim=(-10, np.max(self.y_pred)+9 ) )
        
        plot_planets(measurements, self.ax)
        
        self.spaceship_pred = plt.Circle((0., 0.), 2, fc='r')

        #create a patch for the target
        self.patch_width = 4.6
        self.patch_height = 4.6
        self.target = plt.Rectangle((0-(self.patch_width/2),0-(self.patch_height/2)), self.patch_width, self.patch_height,
                                            linewidth=2,edgecolor='green',facecolor='none') 
       
    
    def init(self):
        
        self.spaceship_pred.center = (0 - (self.patch_width/2), 0 - (self.patch_height/2) )
        self.target.set_xy( (0,0) )
        self.ax.add_patch(self.spaceship_pred)
        self.ax.add_patch(self.target)

        legend_earth = plt.Line2D([0], [0], ls='None', color="blue", marker='o')
        legend_moon = plt.Line2D([0], [0], ls='None', color="grey", marker='o')
        legend_pred = plt.Line2D([0], [0], ls='None', color="red", marker='o')
        
        self.ax.legend([legend_earth, legend_moon, self.target, legend_pred],["Earth","Moon","Target","Prediction"])

        return self.spaceship_pred, self.target,

    
    def animate(self,i):
        
        x, y = self.x_pred[i], self.y_pred[i]

        x_t, y_t = self.x_target[i], self.y_target[i]

        self.spaceship_pred.center=(x,y)
        self.target.set_xy( (x_t - self.patch_width/2, y_t - self.patch_height/2) )

        return self.spaceship_pred, self.target,
    
    def save_and_visualize_animation(self, path):
        
        anim= FuncAnimation(fig=self.fig, func=self.animate, init_func=self.init,frames=len(self.x_pred),interval=50, blit=True)
        
        writer = PillowWriter(fps=25)  
        anim.save(path, writer=writer)
        plt.close()
        with open(path,'rb') as f:
            display(Image(data=f.read(), format='gif'))
