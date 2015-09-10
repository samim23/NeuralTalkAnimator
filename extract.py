#!/usr/bin/python
__author__ = 'Samim.io'

import argparse
import os
import errno
import subprocess
from os import listdir
from os.path import isfile, join
import json
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw 


def createVideo(inputdir,outputdir,framerate):
	global foldername
	print '(6/6) CreateVideo: ' + inputdir
	command = 'ffmpeg -y -r ' + str(framerate) + ' -f image2 -i "' + inputdir + '/frame-%6d.jpg" -c:v libx264 -pix_fmt yuv420p -tune fastdecode -tune zerolatency -profile:v baseline ' + outputdir
	proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, universal_newlines=True)
	while proc.poll() is None:
		line = proc.stdout.readline()
		print(line + '\n')

	print 'Adding Audio: ' + inputdir
	#filename = inputdir + '/processed_' + foldername + '.mp4'
	filename = 'videos/processed/processed_' + foldername + '.mp4'
	command = 'ffmpeg -y -i '+inputdir+'/movie.mp4 -i '+inputdir+'/output.aac -c copy -bsf:a aac_adtstoasc -map 0:0 -map 1:0 ' + filename
	proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, universal_newlines=True)
	while proc.poll() is None:
		line = proc.stdout.readline()
		print(line + '\n')

def drawOverlay(image,text):
	print 'drawOverlay: ' + image + ' text: ' + text
	img = Image.open(image)
	draw = ImageDraw.Draw(img)
	font = ImageFont.truetype("font.ttf", 46)
	draw.text((20, 10),text,(255,255,255),font=font)
	img.save(image)


def createImageOverlay(inputdir,framerate):
	print '(5/6) createImageOverlay: ' + inputdir
	foundimages = []
	with open(inputdir + '/result_struct.json') as data_file:    
	    data = json.load(data_file)
	    images = data['imgblobs']
	    for image in images:
	    	imgpath = image['img_path']
	    	imgtext = image['candidate']['text'] # '('+str(image['candidate']['logprob']) +') ' + 
	    	newImage = [imgpath,imgtext]
	    	foundimages.append(newImage)

	frames = [ f for f in listdir(inputdir) if isfile(join(inputdir,f)) ]
	currenttext = ''
	print 'Creating Image Overlay For ' + str(len(frames)) + ' frames'
	for frame in frames:
		if frame.endswith('.jpg') or frame.endswith('.png'):
			for item in foundimages:
			    if item[0] == frame:
			    	currenttext = item[1]
			drawOverlay(inputdir + '/' + frame,currenttext)   

	createVideo(inputdir,inputdir+'/movie.mp4',framerate)


def getImageSentence(inputdir,framerate):
	print '(4/6) getImageSentence: ' + inputdir
	command = 'python predict_on_images.py cv/model_checkpoint_coco_visionlab43.stanford.edu_lstm_11.14.p -r ' + inputdir
	proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, universal_newlines=True)
	while proc.poll() is None:
		line = proc.stdout.readline()
		print(line)

	createImageOverlay(inputdir,framerate)


def getImageFeatures(inputdir,framerate):
	print '(3/6) getImageFeatures: ' + inputdir
	command = 'python python_features/extract_features.py --caffe /caffe --model_def python_features/deploy_features.prototxt --model python_features/VGG_ILSVRC_16_layers.caffemodel --files '+inputdir+'/tasks.txt --out '+inputdir+'/features'
	proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, universal_newlines=True)
	while proc.poll() is None:
		line = proc.stdout.readline()
		print(line)

	getImageSentence(inputdir,framerate)


def addToList(inputdir,frameFreq,framerate):
	print '(2/6) addToList: ' + inputdir
	frames = [ f for f in listdir(inputdir) if isfile(join(inputdir,f)) ]
	counter = frameFreq
	open(inputdir + '/tasks.txt', 'w').close()
	for frame in frames:
		if frame.endswith('.jpg') or frame.endswith('.png'):
			if counter >= frameFreq:
				print frame
				with open(inputdir + '/tasks.txt', 'a') as textfile:
					textfile.write(frame + '\n')
				counter = 0
			counter += 1

	getImageFeatures(inputdir,framerate)


def extractVideo(inputdir, outputdir,framefreq):
    if not os.path.exists(outputdir):
        os.makedirs(outputdir)
    print('(1/6) extractVideo: ' + inputdir + ' To: ' + outputdir)

    # get framerate
    command = 'ffmpeg -i '+inputdir+' 2>&1 | sed -n "s/.*, \(.*\) fp.*/\\1/p"'
    framerate = '24'
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, universal_newlines=True)
    while proc.poll() is None:
    	line = proc.stdout.readline()
    	if len(line) > 1: framerate = line.rstrip('\n')
    
    print 'framerate: ' + framerate

    # get video
    command = 'ffmpeg -i ' + inputdir + ' -framerate '+str(framerate)+' -y -f image2 ' + outputdir + '/frame-%06d.jpg'
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, universal_newlines=True)
    while proc.poll() is None:
        line = proc.stdout.readline()
        #print(line + '\n')

	print('extracting audio: ' + inputdir + ' To: ' + outputdir)

	# get audio
	command = 'ffmpeg -i '+inputdir+' -y -map 0:1 -vn -acodec copy '+outputdir+'/output.aac'
	proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, universal_newlines=True)

	while proc.poll() is None:
		line = proc.stdout.readline()
		#print(line + '\n')

    addToList(outputdir,framefreq, framerate)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='VideoCaptionGenerator')    
    parser.add_argument('-f', '--captionfrequency', help='Caption Creation Frequency Per Frame.', type=int, required=False)
    args = parser.parse_args()

    captionfrequency = args.captionfrequency
    if args.captionfrequency is None:
        captionfrequency = 30

	print '***************************************'
	print '******** GENERATING CAPTIONS **********'
	print '***************************************'
	print 'captionfrequency: ' + str(captionfrequency)

	mypath = 'videos/'
	foldername = ''

	videos = [ f for f in listdir(mypath) if isfile(join(mypath,f)) ]
	for video in videos:
		if video.endswith('.mp4') or video.endswith('.mov') or video.endswith('.avi'):
			print 'Processing: ' + video
			foldername = os.path.splitext(video)[0]
			extractVideo(mypath+video,mypath+foldername,captionfrequency)

	print '********* PROCESSED ALL ************'




