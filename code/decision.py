import numpy as np
import time

#Personality_ouput just puts out some fun text for while the rover is going.
def personality_output(Rover):
   text_out = "StarDate: " + str(round(time.time() - Rover.start_time,2)) + ": " 
   if (Rover.mode_text == "UnStucking"):
        Rover.times_stuck += 1
        print (text_out + "Aww man I'm stuck. How many times has it been? Oh ya " + str(Rover.times_stuck))
   if (Rover.mode_text == "Initializing"):
        print (text_out + "Oh wow! A new world! Time to see what it has to offer! And take it.") 
   if (Rover.mode_text == "Finding Wall"):
        print (text_out + "Plan Zed, find a wall and stick to it!  Where could a wall be?")
   if ((Rover.mode_text == "Wall Holding") & (Rover.last_state == "Finding Wall")):
        print (text_out + "This wall is my own, there are many others like it, but this one is mine!")
   if (Rover.mode_text == "Picking Up Sample"):
        print (text_out + "Oooooooo, SHINY! I MUST HAVE YOU! I MUST HAVE YOU NOW!")
   if ((Rover.mode_text == "Wall Holding") & (Rover.last_state == "Picking Up Sample")):
        print (text_out + "Ooooo, now I have you and you can't ever ever leave.  Where's my wall? Oh ya!")
   if (Rover.mode_text == "Going Home"):
        print (text_out + "Man I'm tired after picking up all those six rocks. Time to go back home and await pick up.")
   if (Rover.mode_text == "At Home!"):
        print (text_out + "I'm BACK. Ok NASA, ready for pick up!  NASA??? NASA???? HELLLLOOOOOOOO?!")

#Move_Towards_Goal is when the Rover is given a goal to focus on. It will be either a rock sample or the home coordinates
def move_towards_goal(Rover, pos):
    #We only want to crawl to the target
    if (Rover.vel >= Rover.crawl_vel):
        Rover.brake = 10
        Rover.throttle = 0
        Rover.steer = 0
    else:

        Rover.brake = 0
        #Find the angle of attack
        target_yaw = np.arctan2(int(pos[1]) - int(Rover.pos[1]),int(pos[0]) - int(Rover.pos[0]))

        #If we have a negative angle, increase it before we figure it out
        if (target_yaw < 0):
           target_yaw += np.pi * 2
        #Convert to degrees
        target_yaw = target_yaw * 180 / np.pi
        
        #If the rover is to the right of the angle, turn left
        if (round(Rover.yaw + 360,0) < round(target_yaw + 360 - Rover.target_yaw_diff,0)):
           Rover.steer = Rover.goal_turning_speed

        #If the rover is to the left of the angle, turn right
        elif (round(Rover.yaw + 360,0) > round(target_yaw + 360 + Rover.target_yaw_diff,0)):
           Rover.steer = Rover.goal_turning_speed * -1

        #Else we are looking at it, go get it.
        else:
           Rover.brake =0
           Rover.throttle = 0.3
           Rover.steer =0 

    
#Unstuck is what to do if we determine we haven't moved
def unstuck(Rover):
    #THere are two methods, this is the first which is back up while messing with the wheels
    if (Rover.unstuck_method % 2 == 0):
         multi = 1
         if (int(time.time()) % 2 == 0):
              multi = -1
         Rover.steer = -5 * multi
         Rover.brake =0
         if (Rover.vel >= -0.1):
              Rover.throttle = -0.3
         else:
              Rover.throttle = 0
    #This method turns us fast while standing still then guns it.
    if (Rover.unstuck_method % 2 == 1):
         if (int(time.time()) % 2 == 0):
               Rover.throttle = 0
               Rover.steer = 15
               Rover.brake = 0
         else:
               Rover.throttle = 0.4
               Rover.brake = 0
               Rover.steer = 0

#Drive_straight just moves the rover forward, this is used in "Find Wall" state.
def drive_straight(Rover):
    Rover.steer = 0
    Rover.brake = 0    
    
    if (Rover.vel <= Rover.max_vel):   
        Rover.throttle = Rover.throttle_set
    else:
        Rover.throttle = 0

#Stop_Rover is what it sounds like, stops the thing    
def stop_rover(Rover):
    Rover.throttle = 0
    Rover.steer = 0
    Rover.brake = Rover.brake_set

#Right_Hand_Drive is moving the rover along the wall
def right_hand_drive(Rover):
    Rover.steer = Rover.nav_angle
    if (Rover.vel <= Rover.max_vel):
         Rover.throttle = Rover.throttle_set
    else:
         Rover.throttle = 0
    Rover.brake = 0
    

#Spin_Rover is spinning it in place.
def spin_rover(Rover, direction):
    if (Rover.vel > 0):
       stop_rover(Rover)
    else:
        multi = 1

        if (direction == "right" ):
             multi = -1

        Rover.steer = 15 * multi
        Rover.throttle = 0
        Rover.brake = 0
    

# This is where you can build a decision tree for determining throttle, brake and steer 
# commands based on the output of the perception_step() function
def decision_step(Rover):

    #Check Last state vs this state for personality
    if (Rover.mode_text != Rover.last_state):
        personality_output(Rover)
        Rover.last_state = Rover.mode_text
    
    #State initializing is where I set up my first variables like origin pos. This quickly goes into the Finding Wall state
    if (Rover.mode_text == "Initializing"):

          Rover.starting_pos = Rover.pos
          Rover.last_pos = Rover.pos
          Rover.mode_text = "Finding Wall"
          Rover.mode_before_stuck = Rover.mode_text

    #Unstucking state is if we determine we are stuck.
    elif (Rover.mode_text == "UnStucking"):
         unstuck(Rover)

    #Finding wall state is where we drive forward until we find a wall
    elif (Rover.mode_text == "Finding Wall"):

          if (Rover.at_wall):
               if (Rover.vel == 0):
                   Rover.mode_text = "Wall Holding"
                   Rover.mode_before_stuck = Rover.mode_text
               else:
                   stop_rover(Rover)
          else:
               drive_straight(Rover)

    #Wall holding is the normal state where we are bouncing along the wall until we find a sample.
    elif (Rover.mode_text == "Wall Holding"):
          
          if (Rover.at_wall):
             spin_rover(Rover,"left")
             pass
          else:
             right_hand_drive(Rover)          
             pass

    #Picking up a sample is where we have found a sample, now we have to move towards it and pick it up
    elif (Rover.mode_text == "Picking Up Sample"):
          if (Rover.picking_up == 1):
               Rover.debut_text = "Waiting For PickUp"
               Rover.got_the_goods = True
          else:
               if (Rover.got_the_goods):
                   Rover.got_the_goods = False
                   Rover.set_pickup_protect = False
                   Rover.mode_text = "Wall Holding"
                   Rover.samples_my_count += 1
               else:
                    if (Rover.near_sample):
                         if(Rover.set_pickup_protect):
                            pass
                         else:
                            Rover.set_pickup_protect = True
                            Rover.send_pickup = True
                    else:
                         move_towards_goal(Rover, Rover.target_rock_pos)
    #Once we have all 6 samples, we start the Going Home state which is like "Wall Holding" except it also checks for the home spot
    elif (Rover.mode_text == "Going Home"):

          if (Rover.ready_for_home):
                 move_towards_goal(Rover, Rover.starting_pos)
          else:
                 if (Rover.at_wall):
                    spin_rover(Rover,"left")
                     
                 else:
                    right_hand_drive(Rover)          

    #Final resting state is At Home! when we have all 6 samples and are back in the home spot.    
    elif (Rover.mode_text == "At Home!"):
          Rover.brake = 10
          Rover.throttle = 0
          Rover.steer = 0
          Rover.stuck_check_time = time.time() + 10
          if (Rover.final_time == 0):
               Rover.final_time = time.time()
          Rover.mapping_text = ""
          Rover.debug_text = "Done: " + str(Rover.final_time - Rover.start_time) + "secs"
 
    return Rover

