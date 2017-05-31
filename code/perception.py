import numpy as np
import cv2
import time

#Perspect_Transform takes the source points and transforms them into the destination points. 
#This function was ripped directly from the lectures.
def perspect_transform(img, src, dst):
           
    M = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(img, M, (img.shape[1], img.shape[0]))# keep same size as input image
    
    return warped


#Rover_Coords_Close_Enough looks at all of the points in relation to the rover and filters out ones that are within
#a certain distance to the Rover.  As you get farther away from the Rover the accuracy drops, so this helps
#with Fidelity
def rover_coords_close_enough(xpix, ypix, max_dist):

    good_pixels = np.sqrt(xpix**2 + ypix**2) < max_dist
    xpix_good = xpix[good_pixels]
    ypix_good = ypix[good_pixels]
    return xpix_good, ypix_good


#Find_Obstacle is the function that looks at the image and finds anything that would be classified as an obstacle
#One thing to note is that it will find rock samples as an obstacle. This is by design because if you do not pick
#up the sample, it IS an obstacle. I got caught on it more times than I would like to admit
def find_obstacle(img, rgb_thresh=(160,160,160)):
    color_select = np.zeros_like(img[:,:,0])
    above_thresh = (img[:,:,0] > rgb_thresh[0]) \
                & (img[:,:,1] > rgb_thresh[1]) \
                & (img[:,:,2] > rgb_thresh[2])
    color_select[np.invert(above_thresh)] = 1
    return color_select


#Find_Rock_Sample is the thresholding function to find the rocks.  I used cv2.inRange instead of the other 
#methods because I was having a hard time getting those to work.
def find_rock_sample(img):
    color_select = np.zeros_like(img[:,:,0])
    #Found Example from Slack of using cv2 instead of trying to figure out method like others finds
    low_thresh = np.array([140,100,0], dtype = "uint8")
    high_thresh = np.array([180,180,40], dtype = "uint8")

    mask_rock = cv2.inRange(img, low_thresh, high_thresh)
    return mask_rock
    


#Find_Navigable finds all navigable terrain. This was ripped straight from the lectures.
# Identify pixels above the threshold
# Threshold of RGB > 160 does a nice job of identifying ground pixels only
def find_navigable(img, rgb_thresh=(160, 160, 160)):
    # Create an array of zeros same xy size as img, but single channel
    color_select = np.zeros_like(img[:,:,0])
    # Require that each pixel be above all three threshold values in RGB
    # above_thresh will now contain a boolean array with "True"
    # where threshold was met
    above_thresh = (img[:,:,0] > rgb_thresh[0]) \
                & (img[:,:,1] > rgb_thresh[1]) \
                & (img[:,:,2] > rgb_thresh[2])
    # Index the array of zeros with the boolean array and set to 1
    color_select[above_thresh] = 1
    # Return the binary image
    return color_select

#Rover_coords is the function that takes the warped image and moves them to rover coordinates. Ripped right
#from the lecture.
# Define a function to convert to rover-centric coordinates
def rover_coords(binary_img):
    # Identify nonzero pixels
    ypos, xpos = binary_img.nonzero()
    # Calculate pixel positions with reference to the rover position being at the 
    # center bottom of the image.  
    x_pixel = np.absolute(ypos - binary_img.shape[0]).astype(np.float)
    y_pixel = -(xpos - binary_img.shape[0]).astype(np.float)
    return x_pixel, y_pixel


#To_Polar_Coords is a function that takes world space coordinates and makes them into a vector + rotation.
#This is used to figure out which way to turn. Ripped right from the lecture.
# Define a function to convert to radial coords in rover space
def to_polar_coords(x_pixel, y_pixel):
    # Convert (x_pixel, y_pixel) to (distance, angle) 
    # in polar coordinates in rover space
    # Calculate distance to each pixel
    dist = np.sqrt(x_pixel**2 + y_pixel**2)
    # Calculate angle away from vertical for each pixel
    angles = np.arctan2(y_pixel, x_pixel)
    return dist, angles

# Rotate_pix is used to change the Rover roated coordinates to the world rotated ones. Ripped right from the
#lecture.
# Define a function to apply a rotation to pixel positions
def rotate_pix(xpix, ypix, yaw):

    # Convert yaw to radians
    # Apply a rotation
    yaw_rad = yaw * np.pi / 180
    xpix_rotated = (xpix * np.cos(yaw_rad)) - (ypix * np.sin(yaw_rad))
                            
    ypix_rotated = (xpix * np.sin(yaw_rad)) + (ypix * np.cos(yaw_rad))
    # Return the result  
    return xpix_rotated, ypix_rotated

# Rotate_pix is used to change the Rover roated coordinates to the world rotated ones. Ripped right from the
#lecture.
# Define a function to apply a rotation to pixel positions
def translate_pix(xpix_rot, ypix_rot, xpos, ypos, scale): 

    # Apply a scaling and a translation
    xpix_translated = (xpix_rot / scale) + xpos
    ypix_translated = (ypix_rot / scale) + ypos
    # Return the result  
    return xpix_translated, ypix_translated

# Pix_To_world is the combination of the last 2 functions. It takes rover based cordinates and moves it to world
# based ones.  Ripped right from lecture.
# Define a function to apply rotation and translation (and clipping)
# Once you define the two functions above this function should work
def pix_to_world(xpix, ypix, xpos, ypos, yaw, world_size, scale):
    # Apply rotation
    xpix_rot, ypix_rot = rotate_pix(xpix, ypix, yaw)
    # Apply translation
    xpix_tran, ypix_tran = translate_pix(xpix_rot, ypix_rot, xpos, ypos, scale)
    # Perform rotation, translation and clipping all at once
    x_pix_world = np.clip(np.int_(xpix_tran), 0, world_size - 1)
    y_pix_world = np.clip(np.int_(ypix_tran), 0, world_size - 1)
    # Return the result
    return x_pix_world, y_pix_world



# My perception_step!
def perception_step(Rover):

    #This is my text on the overaly
    Rover.debug_text = ""
    Rover.mapping_text = ""

    #If we are stuck, we have to make sure we are still stuck
    if (Rover.mode_text == "UnStucking"):
          if (np.sqrt((Rover.pos[0]-Rover.last_pos[0])**2 + (Rover.pos[1] - Rover.last_pos[1])**2) >= Rover.stuck_check_distance):
              Rover.mode_text=Rover.mode_before_stuck
              Rover.unstuck_method = 0
    else:

           #We are not stuck, let's see if we are close to home!
           if (Rover.samples_my_count >= 6):
             Rover.mode_text = "Going Home"
             distance_to_home = np.sqrt((Rover.pos[0]-Rover.starting_pos[0])**2 + (Rover.pos[1] - Rover.starting_pos[1])**2)           
             if (distance_to_home <= Rover.distance_to_home_before_action):
                    Rover.ready_for_home = True

             else:
                    Rover.ready_for_home = False
  
             if (distance_to_home <= Rover.distance_to_home_complete):
                 Rover.mode_text = "At Home!"
           
    #Every so often we check if we are stuck, is it that time?           
    if (int(time.time()) == Rover.stuck_check_time):

         #Let's know what we are at before we got stuck, so we can go back to doing that.
         if (Rover.mode_text != "UnStucking"):
              Rover.mode_before_stuck=Rover.mode_text
         Rover.stuck_check_time += Rover.check_seconds
         distance_check = np.sqrt((Rover.pos[0]-Rover.last_pos[0])**2 + (Rover.pos[1] - Rover.last_pos[1])**2)
         if (distance_check < Rover.stuck_check_distance):
              if (Rover.mode_text != "UnStucking"):
                    Rover.mode_before_stuck = Rover.mode_text
              #Oh no we stuck
              Rover.mode_text="UnStucking"
              Rover.unstuck_method += 1
         else:
              Rover.mode_text=Rover.mode_before_stuck
              Rover.unstuck_method = 0
         Rover.last_pos = Rover.pos
               


    #If pitch or roll is over our allowed, then we skip the image processing
    if ((Rover.pitch >= Rover.bad_pitch) & (Rover.pitch <= 360 - Rover.bad_pitch)):
        Rover.mapping_text = "Bad Pitch"
        Rover.vision_image = np.zeros_like(Rover.img)
    elif ((Rover.roll >= Rover.bad_roll) & (Rover.roll <= 360 - Rover.bad_roll)):
        Rover.mapping_text = "Bad Roll"
        Rover.vision_image = np.zeros_like(Rover.img)

    #Good pitch and roll
    else:

        Rover.mapping_text = "Mapping"
        Rover.vision_image = np.zeros_like(Rover.img)

        #Set up our size and source/destination for transforming. This is ripped right from the lecture
        dst_size = 5 
        bottom_offset = 6
        source = np.float32([[14, 140], [301 ,140],[200, 96], [118, 96]])
        destination = np.float32([[Rover.img.shape[1]/2 - dst_size, Rover.img.shape[0] - bottom_offset],
                  [Rover.img.shape[1]/2 + dst_size, Rover.img.shape[0] - bottom_offset],
                  [Rover.img.shape[1]/2 + dst_size, Rover.img.shape[0] - 2*dst_size - bottom_offset], 
                  [Rover.img.shape[1]/2 - dst_size, Rover.img.shape[0] - 2*dst_size - bottom_offset],
                  ])
	
        #Getting the navigable mask
        warped = perspect_transform(Rover.img, source, destination)
        navigable = find_navigable(warped)

        #Getting the obstacle mask
        obstacle_pre_warp = find_obstacle(Rover.img)
        obstacle = perspect_transform(obstacle_pre_warp, source, destination)

        #Getting the rock sample mask
        rock_sample_pre_warp = find_rock_sample(Rover.img)
        rock_sample = perspect_transform(rock_sample_pre_warp, source, destination)

        #Updating our rover vision with the masks
        Rover.vision_image[:,:,0] = obstacle * 255
        Rover.vision_image[:,:,1] = rock_sample * 255
        Rover.vision_image[:,:,2] = navigable * 255

        #Making the pixels into rover coordinates
        xpix_ob, ypix_ob = rover_coords(obstacle)
        xpix_rs, ypix_rs = rover_coords(rock_sample)
        xpix_nav, ypix_nav = rover_coords(navigable)

        #Eliminating coordinates that are farther away than we want
        xpix_ob_close, ypix_ob_close = rover_coords_close_enough(xpix_ob, ypix_ob, Rover.find_max_distance)
        xpix_rs_close, ypix_rs_close = rover_coords_close_enough(xpix_rs, ypix_rs, Rover.find_rock_max_distance) #Samples use different amount
        xpix_nav_close, ypix_nav_close = rover_coords_close_enough(xpix_nav, ypix_nav, Rover.find_max_distance)

        # Converting rover coords to world coords
        ypix_ob_world, xpix_ob_world = pix_to_world(xpix_ob_close, ypix_ob_close, Rover.pos[0], Rover.pos[1], Rover.yaw, 200, 10)
        ypix_rs_world, xpix_rs_world = pix_to_world(xpix_rs_close, ypix_rs_close, Rover.pos[0], Rover.pos[1], Rover.yaw, 200, 10)
        ypix_nav_world, xpix_nav_world = pix_to_world(xpix_nav_close, ypix_nav_close, Rover.pos[0], Rover.pos[1], Rover.yaw, 200, 10)


        #Updating our worldmap with what we found
        Rover.worldmap[xpix_ob_world, ypix_ob_world, 0] = 255    
        Rover.worldmap[xpix_rs_world, ypix_rs_world, 1] = 255
        Rover.worldmap[xpix_nav_world, ypix_nav_world, 2] = 255

        #IF we do not have enough navigable coordinates, that means we are at a wall
        if(len(xpix_nav_close) < Rover.close_pixs_for_wall_detection):
            Rover.at_wall = True
        else:
            Rover.at_wall = False

        
        #Get the polar coordinates to figure out the angle to move
        distances, angles = to_polar_coords(xpix_nav_close, ypix_nav_close)

        #In case we have 0 angles and I do not want to numpy's warning about it
        if (angles.size > 0):
             avg_angle = np.mean(angles)
             #Our angle is the average angle minus what we call the perfect angle. This keeps us hugging the wall
             Rover.nav_angle = (avg_angle - Rover.perfect_angle) * 180.0 / np.pi

        #If we see a rock and we aren't stuck, go get that rock!
        if ((len(ypix_rs_world)>5) & (Rover.mode_text != "UnStucking")):
             Rover.target_rock_pos = (np.mean(ypix_rs_world[ypix_rs_world > 0]),np.mean(xpix_rs_world[xpix_rs_world >0])) 
             Rover.mode_text = "Picking Up Sample"
         
   
    return Rover
