'''
Based on 
https://github.com/samyk/magspoof.git
https://github.com/joshlf/magspoof.git
https://github.com/miaoski/magspoof.git

rewrite by devBioS in python and modified for interpacket delay 
'''

import time
from machine import Pin
import machine, neopixel, network
from config import tracks

np = neopixel.NeoPixel(machine.Pin(4), 4)
'''
 Def:
 Track 0 is the 1st track on card
 Track 1 is the 2nd track on card
 Track 2 is the 3rd track on card

 From http://msrtron.com/blog-headlines/blog-card-data
 
  All cards have 3 tracks on the magnetic stripe, this is an industry standard.  
  Each track holds different card data. 
  However, ONLY track 1 and track 2 have data, track 3 is always blank.  
  For these cards a reader which is able to read all 3 tracks and a reader which only reads track 1&2 will work exactly the same.  
  There is no benefit to reading track 3 on financial cards.
 
  Track 0 starts most of the time with % sign and can include Text
  ----------------------------------------------------------------
    contains the same information [as Track 1] with the addition of the cardholder name. 
    Generally the name is shown in the format of last name (surname) then first name, but it 
    can also be shown first name then last name, this varies depending on the issuing bank. 
    This track is much less important.
    Format: %B(cardnumber)^(lastname)/(firstname)^(expiration)(service code)(discretionary data)?
 
 
  Track 1 is most important starts always with ; and end with ?
  ----------------------------------------------------------------
   The track contains the following information and format:
   Format: ;(Cardnumber)=(expiration)(service code)(discretionary data)?
'''

# subtract and len bits defined per track
# track 0 nees sublen 32 with bitlen 7 - else text won't be correctly interpreted
# track 1 & 2 needs sublen 48 with bitlen 5
sublen = [32,48,48]
bitlen=[7,5,5]


between_zero = 53 #53 zeros between track 0 & 1
clock_us = 240 # 240 works best for me
interpacket_us = 10 # 10 works best for me
pause_between_send = 3 #3 seconds pause between each send attempt

# outputpin to transistor
pn = Pin(16,Pin.OUT)
pn.value(0)

# inputpin to activate the send-function
pinsend = Pin(12,Pin.IN)

# inputpin to activate WLAN
pinwlan = Pin(13,Pin.IN)

# disable WLAN
sta_if = network.WLAN(network.STA_IF)
ap_if = network.WLAN(network.AP_IF)
# uncomment to define an ESSID and password yourself instead of the micropython defaults
#ap_if.config(essid="RedSpoof", authmode=network.AUTH_WPA_WPA2_PSK, password="thaP4ssw0rd")
sta_if.active(False)
ap_if.active(False)

# needed for reversing the track
revTrack = [0 for x in range(41)]
dir = 0

# send a "Bit"
def playBit(sendBit):
  global dir, clock_us, pn
  dir ^= 1;
  pn.value(dir)
  time.sleep_us(clock_us);

  if (sendBit):
    dir ^= 1;
    pn.value(dir)
  time.sleep_us(clock_us);

# send a single track from "tracks" in forward direction
# this function first stores all "Bits" and then send them in a single transaction because
# I had timing problems when you send it "live" as in the original code
def playTrack(track,tracks):
    global dir
    tmp = 0
    crc = 0
    lrc=0
    dir=0
    send = []

    #start with 25 0's
    for i in range(0,25):
      send.append(0)

    #calculate each char into bits 
    for chr in tracks[track]:
      crc = 1
      tmp = ord(chr) - sublen[track]
      j = 0
      while (j < bitlen[track] -1):
          crc ^= (tmp & 1)
          lrc ^= (tmp & 1) << j
          send.append(tmp & 1)
          tmp >>= 1
          j+=1
      send.append(crc)
    
    #finish calculating and send last "byte" (LRC)
    tmp = lrc
    crc = 1
    j = 0
    while (j < bitlen[track] -1):
      crc ^= (tmp & 1)
      send.append(tmp & 1)
      tmp >>= 1
      j+=1
    send.append(crc)

    #finish with 25 0's
    for i in range(0,25):
      send.append(0)

    #send the whole bunch of bits
    for x in send:
      playBit(x)
      time.sleep_us(interpacket_us);
    
    #turn off power to the transistor
    pn.value(0)
      
def playTracks(tracks):
    global dir, revTrack, pn
    tmp = 0
    crc = 0
    lrc=0
    dir=0
    send = []
    #print("Playing %s" % tracks[track])
    
    #start with 25 0's
    for i in range(0,25):
      send.append(0)
    
    #store Track 0 in send array (forward slide)
    for chr in tracks[0]:
      crc = 1
      tmp = ord(chr) - sublen[0]
      j = 0
      while (j < bitlen[0] -1):
          crc ^= (tmp & 1)
          lrc ^= (tmp & 1) << j
          send.append(tmp & 1)
          tmp >>= 1
          j+=1
      send.append(crc)
    
    #finish calculating and send last "byte" (LRC)
    tmp = lrc
    crc = 1
    j = 0
    while (j < bitlen[0] -1):
      crc ^= (tmp & 1)
      send.append(tmp & 1)
      tmp >>= 1
      j+=1
    send.append(crc)
    
    #store 0's between the tracks
    for i in range(0,between_zero):
        send.append(0)

    #store Track 1 in send array (reverse slide)
    storeRevTrack(1)     
    for chr in reversed(revTrack):
      j = bitlen[1]-1
      while (j >= 0):
          send.append((chr >> j ) & 1 )
          j-=1  
    
    #finish with 25 0's
    for i in range(0,25):
      send.append(0)

    #send the whole bunch of bits
    for x in send:
      playBit(x)
      time.sleep_us(interpacket_us);

    #turn off power to the transistor      
    pn.value(0)

# caluclate the reverse track and store in revTrack for usage later in sendTracks function
def storeRevTrack(track):
    global revTrack
    tmp = 0
    crc = 0
    lrc=0
    dir=0
    i=0
    #calculate each char into bits
    for chr in tracks[track]:
      crc = 1
      tmp = ord(chr) - sublen[track]
      j = 0
      while (j < bitlen[track] -1):
          crc ^= tmp & 1
          lrc ^= (tmp & 1) << j
          if (tmp & 1):
            revTrack[i] |= 1 << j
          else:
            revTrack[i] &= ~(1<<j)
          tmp >>= 1
          j+=1
          
      if (crc):
          revTrack[i] |= 1 << 4
      else:
          revTrack[i] &= ~(1<<4)
    
      i+=1
    
    #finish calculating and send last "byte" (LRC)
    tmp = lrc
    crc = 1
    j = 0
    while (j < bitlen[track] -1):
      crc ^= tmp & 1
      if (tmp & 1):
          revTrack[i] |= 1 << j
      else:
          revTrack[i] &= ~(1<<j)
      tmp >>=1
      j+=1
    if (crc):
      revTrack[i] |= 1 << 4
    else:
      revTrack[i] &= ~(1<<4)
    
    
def startsendtrack():
  from config import tracks
  #LED Mode to show we are preparing to send
  np[3] = (10, 0, 10)
  np[1] = (10, 0, 10)
  np.write()
  time.sleep(1)
  
  #send as long as one of the buttons is not pressed again
  while(pinsend.value() == 1):
    np[3] = (3, 0, 0)
    np[1] = (3, 0, 0)
    np.write()

    if (tracks[0] != "" and tracks[1] != ""):
    	playTracks(tracks) #send Track 0 forward, Track 1 in reverse
    elif (tracks[0] != "" and tracks[1] == ""):
      playTrack(0,tracks) #send Track 0 forward
    elif (tracks[0] == "" and tracks[1] != ""):
      playTrack(1,tracks) #send Track 1 forward
      
    np[3] = (0, 0, 0)
    np[1] = (0, 0, 0)
    np.write()
    time.sleep(pause_between_send)

#start WLAN and activate webserver
def startwlan():
   ap_if.active(True)
   import webserver
   webserver.main()

np[0] = (10, 10, 10)
np[1] = (10, 10, 10)
np[2] = (10, 10, 10)
np[3] = (10, 10, 10)
np.write()

#for easier debugging when on REPL
def debugplay():
    while(True):
        playTracks(tracks)
        time.sleep(3)


while(1):
   np[0] = (0, 0, 0)
   np[1] = (0, 0, 0)
   np[2] = (0, 0, 0)
   np[3] = (0, 0, 0)
   np.write()
   #send button pressed
   if (pinsend.value() == 0):
      ap_if.active(False)
      startsendtrack()
   #WLAN button pressed   
   if (pinwlan.value() == 0):
      np[0] = (0, 0, 10)
      np[1] = (0, 0, 10)
      np[2] = (0, 0, 10)
      np[3] = (0, 0, 10)      
      np.write()
      startwlan()
   np[0] = (10, 10, 10)
   np[1] = (10, 10, 10)
   np[2] = (10, 10, 10)
   np[3] = (10, 10, 10)
   np.write()
   time.sleep(0.5)

