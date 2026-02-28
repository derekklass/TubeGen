'''
FreeCAD Tube Generation Script

This script parses parameters from PieceMaker and translates them into FreeCAD commands to generate a 3D model of the specified tube.

Created by Derek Klass & John Black
7/24/20
Copyright 2020-2021 Electro-Mechanical Integrators, Inc.
'''


# import FreeCAD scripting modules and python tools
import FreeCAD, PartDesign, Sketcher, Mesh, Part
import math, os, csv


# instantiante global variables
sketch_counter = 0
material_type = 0

# set file location paths and run generation functions
def set_paths():

	# set user profile path
	userprofile = os.environ['USERPROFILE']

	# set STLFile.csv and PieceDefault.stl path
	csv_file = os.path.join(userprofile, 'Documents', 'PieceMaker Docs', 'Resources', 'CSV-STL', 'STLFile.csv')
	stl_file = os.path.join(userprofile, 'Documents', 'PieceMaker Docs', 'Resources', 'CSV-STL', 'PieceDefault.stl')

	# check if Windows 8+ path exists, if not change to Windows 7-
	if not os.path.exists(csv_file):
		csv_file = os.path.join(userprofile, 'My Documents', 'PieceMaker Docs', 'Resources', 'CSV-STL', 'STLFile.csv')
		stl_file = os.path.join(userprofile, 'My Documents', 'PieceMaker Docs', 'Resources', 'CSV-STL', 'PieceDefault.stl')

	# OneDrive
	#csv_file = os.path.join(userprofile, 'OneDrive', 'Documents', 'PieceMaker Docs', 'Resources', 'CSV-STL', 'STLFile.csv')
	#stl_file = os.path.join(userprofile, 'OneDrive', 'Documents', 'PieceMaker Docs', 'Resources', 'CSV-STL', 'PieceDefault.stl')

	# import parameters from csv and run tube generation
	feat_length, material_type = import_parameters(csv_file)

	# import features from csv and run feature generation
	import_features(csv_file, feat_length, material_type)

	# export generated tube to PieceDefault.stl
	Mesh.export(__objs__, stl_file)


'''PARAMETER IMPORT'''
# import parameters from csv and run tube generation
def import_parameters(csv_file):

	# read in parameters
	with open(csv_file) as csvfile:
		csv_reader = csv.reader(csvfile)
		row_count = 0

		for row in csv_reader:
			if row_count == 1:
				material_type = int(row[2])
				diameter = float(row[5]) * 25.4
				wall = float(row[6]) * 25.4
				roffset = float(row[7])
				length = float(row[8]) * 25.4
				e1join = float(row[9]) * 25.4
				e1angle = float(row[10])
				e2join = float(row[12]) * 25.4
				e2angle = float(row[13])
				e1flat = str(row[27]).strip()
				e2flat = str(row[28]).strip()
				side1 = float(row[43]) * 25.4
				side2 = float(row[44]) * 25.4
				cradius = float(row[45]) * 25.4
				e1cutside = int(row[46])
				e2cutside = int(row[47])
			row_count += 1

	# initialize length used for calculating feature location, default is 'length', which is only used for round
	feat_length = length

	''' # using a similar method that works for now
	# calculate correct length to extrude in FreeCAD
	if material_type != 0:  # if not round
		if roffset in [0,180]:
			e1adjust = side1/(2*math.tan(math.radians(e1angle)))
			e2adjust = side1/(2*math.tan(math.radians(e2angle)))
		elif roffset in [90,270]:
			e1adjust = side2/(2*math.tan(math.radians(e1angle)))
			e2adjust = side2/(2*math.tan(math.radians(e2angle)))

		# feature position is calculated as 'x_feat_loc = -length + xdist'
		# include only e2adjust for feat_length b/c the starting point for features is on the right of the tube (e2)
		feat_length = length + e2adjust
		length = length + e1adjust + e2adjust
	'''

	# using material type, generate appropriate tube
	if material_type == 1:  # round
		round_tube(diameter, wall, length, roffset, e1angle, e2angle, e1flat, e2flat, e1join, e2join)

	elif material_type == 2:  # rectangular
		if roffset == 90:
			roffset = 270
		elif roffset == 270:
			roffset = 90
		rectangular_tube(side1, side2, wall, cradius, length, roffset, e1angle, e2angle, e1cutside, e2cutside)

	elif material_type == 3:  # angle iron
		angle_iron_tube(side1, side2, wall, cradius, length, roffset, e1angle, e2angle, e1cutside, e2cutside)

	elif material_type == 4:  # flat bar
		flat_bar_tube(side1, side2, wall, cradius, length, roffset, e1angle, e2angle, e1cutside, e2cutside)

	elif material_type == 5:  # c-channel
		c_channel_tube(side1, side2, wall, cradius, length, roffset, e1angle, e2angle, e1cutside, e2cutside)

	elif material_type == 6:  # flat bar
		i_beam_tube(side1, side2, wall, cradius, length, roffset, e1angle, e2angle, e1cutside, e2cutside)

	# return length for features, and material_type
	return feat_length, material_type

# import features from csv and run feature generation
def import_features(csv_file, feat_length, material_type):

	# import feature data
	with open(csv_file) as csvfile:
		csv_reader = csv.reader(csvfile)
		line_count = 0

		# header data from the csv to be read (UPDATE IF DIFFERENT FEATURE INFO IS NEEDED)
		feature_data_needed = ['DescType', 'XDistance', 'ROS', 'Diameter', 'Seperation', 'XDistance_Y', 'ArrayIncrement', 'ArrayInstances', 'Orientation_0', 'Orientation_90', 'Orientation_180', 'Orientation_270', 'ArrayIncrement_Y', 'ArrayInstances_Y', 'ArrayIncrement_A', 'ArrayInstances_A']

		# store lists with each feature data
		feature_list = []

		# read through each row of csv file
		for row in csv_reader:
			if line_count == 2:  # feature headers

				feature_data_indexes = []

				# save the indexes of each necessary piece of data in a list
				for header in feature_data_needed:
					feature_data_indexes.append(row.index(header))

			elif line_count >= 3:  # feature data

				# temporary storage for feature data
				feature_data = []

				# add necessary data to list
				for i in feature_data_indexes:
					feature_data.append(float(row[i]))

				if material_type == 5:  # c-channel, rotate feature degrees by 90, counter clockwise
#					feature_temp = feature_data[11]
#					feature_data[11] = feature_data[10]
#					feature_data[10] = feature_data[9]
#					feature_data[9] = feature_data[8]
#					feature_data[8] = feature_temp

					if feature_data[0] == 0:  # circle - 0 needs to be swapped with 270
						feature_temp = feature_data[9]
						feature_data[9] = feature_data[11]
						feature_data[11] = feature_temp
					if feature_data[0] == 1:  # slot - 0 needs to be swapped with 270
						feature_temp = feature_data[9]
						feature_data[9] = feature_data[11]
						feature_data[11] = feature_temp
					if feature_data[0] == 4:  # rectangle - 0 needs to be swapped with 270
						feature_temp = feature_data[9]
						feature_data[9] = feature_data[11]
						feature_data[11] = feature_temp

				# add list for each feature to collective list
				feature_list.append(feature_data)

			line_count += 1

	# using DescType, generate appropriate features with defined parameters
	for feature in feature_list:
		if feature[0] == 0:  # circle
			print('Circle Feature: ', feature)
			# print (str(feature[13])+ ": " + str(feature[13]) +": " + str(feature[14])+": " + str(feature[15]))
			for i in range(0, int(feature[13])):
				# print (str(i) + ": " + str(feature[13]))
				print (feature)
				circle_feature(feature[1] * 25.4, feature[2], feature[3] * 25.4, (feature[5] + i*feature[12]) * 25.4, feature[6] * 25.4, int(feature[7]), feat_length, material_type, bool(int(feature[8])), bool(int(feature[11])), bool(int(feature[10])), bool(int(feature[9])))
		elif feature[0] == 1:  # slot
			print('Slot Feature: ', feature)
			# print (str(feature[13])+ ": " + str(feature[13]) +": " + str(feature[14])+": " + str(feature[15]))
			for i in range(0, int(feature[13])):
				# print (str(i) + ": " + str(feature[13]))
				slot_feature(feature[1] * 25.4, feature[2], feature[3] * 25.4, feature[4] * 25.4, (feature[5] + i*feature[12]) * 25.4, feature[6] * 25.4, int(feature[7]), feat_length, material_type, bool(int(feature[8])), bool(int(feature[9])), bool(int(feature[10])), bool(int(feature[11])))
		elif feature[0] == 4:  # rectangle
			print('Rectangle Feature: ', feature)
			# print (str(feature[13])+ ": " + str(feature[13]) +": " + str(feature[14])+": " + str(feature[15]))
			for i in range(0, int(feature[13])):
				# print (str(i) + ": " + str(feature[13]))
				rectangle_feature(feature[1] * 25.4, feature[2], feature[3] * 25.4, feature[4] * 25.4, (feature[5] + i*feature[12]) * 25.4, feature[6] * 25.4, int(feature[7]), feat_length, material_type, bool(int(feature[8])), bool(int(feature[9])), bool(int(feature[10])), bool(int(feature[11])))
		else:  # undefined
			print('Undefined Feature: ', feature)


'''TUBE GENERATION'''
# generate round tube STL file
def round_tube(diameter, wall, length, roffset, e1angle, e2angle, e1flat, e2flat, e1join, e2join):

	# create new part with the PartDesign workbench
	App.newDocument("RoundTube")
	App.activeDocument().addObject('PartDesign::Body','Body')

	# create sketch on the front plane
	App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch')
	App.activeDocument().Sketch.Support = (App.activeDocument().XZ_Plane, [''])
	App.activeDocument().Sketch.MapMode = 'FlatFace'

	# calculate position of inner circle
	radius = diameter / 2
	inner_radius = radius - wall

	# sketch outer and inner circles
	App.ActiveDocument.Sketch.addGeometry(Part.Circle(App.Vector(0,0,0),App.Vector(0,0,1),radius),False)
	App.ActiveDocument.Sketch.addGeometry(Part.Circle(App.Vector(0,0,0),App.Vector(0,0,1),inner_radius),False)

	# consider end cuts (center-to-center) in length calculation NEEDS WORK
	if e1angle == 90 and e1flat=='True':
		if e2angle == 90 and e2flat=='True':
			length = length

		else:
			length = length + (diameter * math.tan(math.radians(90 - e2angle)) / 2) # () is midpoint of endcut from top-axis

	elif e2angle == 90 and e1flat=='True':
		if e2angle == 90 and e2flat=='True':
			length = length
		else:

			length = length + (diameter * math.tan(math.radians(90 - e1angle)) / 2)

	else:
		length = length +  (diameter * math.tan(math.radians(90 - e1angle)) / 2) + (diameter * math.tan(math.radians(90 - e2angle)) / 2)

	# boss extrude the sketch
	App.activeDocument().Body.newObject("PartDesign::Pad","Pad")
	App.activeDocument().Pad.Profile = App.activeDocument().Sketch
	App.ActiveDocument.Pad.Length = length
	App.ActiveDocument.recompute()

	# determine location of end cuts
	y = diameter / 2
	x1 = -length
	x = -diameter / math.tan(math.radians(e2angle))
	x2 = x1 + (diameter / math.tan(math.radians(e1angle)))

	# determine radius for coped cuts
	if e1join == 0: # avoid divide by 0
		e1join = 1
	if e2join == 0:
		e2join = 1

	e1cope_radius = e1join / 2
	e2cope_radius = e2join / 2

	# determine if first end cut is flat, angled, or coped
	if e1angle != 90 and e1flat == 'True':  # angled flat cut

		# create sketch for first end cut (right plane)
		App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch001')
		App.activeDocument().Sketch001.Support = (App.activeDocument().YZ_Plane, [''])
		App.activeDocument().Sketch001.MapMode = 'FlatFace'

		# sketch first end cut
		App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(x1,-y,0),App.Vector(x2,y,0)),False)
		App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(x2,y,0),App.Vector(x1,y,0)),False)
		App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(x1,y,0),App.Vector(x1,-y,0)),False)

		# extrude cut the first end cut
		App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket")
		App.activeDocument().Pocket.Profile = App.activeDocument().Sketch001
		App.ActiveDocument.Pocket.Length = 1000000
		App.ActiveDocument.Pocket.Length2 = 1000000
		App.ActiveDocument.Pocket.Type = 4
		App.ActiveDocument.recompute()

	elif e1flat == 'False' and e1angle == 90:  # cope / angled cope

		# adjust for cope
		e1angle = 90 - e1angle

		# create plane for sketch for first end cut (angled cope)
		App.getDocument('RoundTube').getObject('Body').newObject('PartDesign::Plane','DatumPlane')

		# position plane
		App.getDocument("RoundTube").DatumPlane.Placement=App.Placement(App.Vector(0,-length,0), App.Rotation(App.Vector(1,0,0),-e1angle), App.Vector(0,0,0))

		# create sketch for first end cut (right plane)
		App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch001')
		App.activeDocument().Sketch001.Support = (App.activeDocument().DatumPlane, [''])
		App.activeDocument().Sketch001.MapMode = 'FlatFace'
		App.ActiveDocument.recompute()

		# sketch angled cope
		App.ActiveDocument.Sketch001.addGeometry(Part.Circle(App.Vector(0,0,0),App.Vector(0,0,1),e1cope_radius),False)

		# extrude cut the first end cut
		App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket")
		App.activeDocument().Pocket.Profile = App.activeDocument().Sketch001
		App.ActiveDocument.Pocket.Length = 1000000
		App.ActiveDocument.Pocket.Length2 = 1000000
		App.ActiveDocument.Pocket.Type = 4
		App.ActiveDocument.recompute()

	# determine if second end cut is flat, angled, or coped
	if e2angle != 90 and e2flat == 'True':  # angled flat cut

		# create sketch for second end cut (right plane)
		App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch002')
		App.activeDocument().Sketch002.Support = (App.activeDocument().YZ_Plane, [''])
		App.activeDocument().Sketch002.MapMode = 'FlatFace'

		# position plane and adjust for roffset
		App.getDocument('RoundTube').getObject('Sketch002').AttachmentOffset = App.Placement(App.Vector(0,0,0),App.Rotation(App.Vector(1,0,0),-roffset))

		# sketch second end cut
		App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(0,-y,0),App.Vector(x,y,0)),False)
		App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(x,y,0),App.Vector(0,y,0)),False)
		App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(0,y,0),App.Vector(0,-y,0)),False)

		# extrude cut the second end cut
		App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket001")
		App.activeDocument().Pocket001.Profile = App.activeDocument().Sketch002
		App.ActiveDocument.Pocket001.Length = 1000000
		App.ActiveDocument.Pocket001.Length2 = 1000000
		App.ActiveDocument.Pocket001.Type = 4
		App.ActiveDocument.recompute()

	elif e2flat == 'False' and e2angle == 90:  # cope / angled cope

		# adjust for cope
		e2angle = 90 - e2angle

		# create plane for sketch for second end cut (angled cope)
		App.getDocument('RoundTube').getObject('Body').newObject('PartDesign::Plane','DatumPlane001')

		# position plane and adjust for roffset
		App.getDocument("RoundTube").DatumPlane001.Placement=App.Placement(App.Vector(0,0,0), App.Rotation(0,-roffset,e2angle), App.Vector(0,0,0))

		# create sketch for second end cut (right plane)
		App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch002')
		App.activeDocument().Sketch002.Support = (App.activeDocument().DatumPlane001, [''])
		App.activeDocument().Sketch002.MapMode = 'FlatFace'
		App.ActiveDocument.recompute()

		# sketch angled cope
		App.ActiveDocument.Sketch002.addGeometry(Part.Circle(App.Vector(0,0,0),App.Vector(0,0,1),e2cope_radius),False)

		# extrude cut the second end cut
		App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket001")
		App.activeDocument().Pocket001.Profile = App.activeDocument().Sketch002
		App.ActiveDocument.Pocket001.Length = 1000000
		App.ActiveDocument.Pocket001.Length2 = 1000000
		App.ActiveDocument.Pocket001.Type = 4
		App.ActiveDocument.recompute()


	# rotate tube to fit in PieceMaker viewing window
	App.getDocument("RoundTube").Body.Placement=App.Placement(App.Vector(0,0,0), App.Rotation(90,0,0), App.Vector(0,0,0))

	# render and save STL file
	global __objs__
	__objs__=[]
	__objs__.append(FreeCAD.getDocument("RoundTube").getObject("Body"))

# generate rectangular tube STL file
def rectangular_tube(side1, side2, wall, cradius, length, roffset, e1angle, e2angle, e1cutside, e2cutside):

	if e1angle < 0:
		e1angle = 360 - e1angle
	if e2angle < 0:
		e2angle = 360 - e2angle

	# calculate positions of corners for square face
	outer_x = 0.5 * side2
	outer_y = 0.5 * side1

	inner_x = outer_x - wall
	inner_y = outer_y - wall

	# create new part with the PartDesign workbench
	App.newDocument("RectangularTube")
	App.activeDocument().addObject('PartDesign::Body','Body')

	# create sketch on the front plane
	App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch')
	App.activeDocument().Sketch.Support = (App.activeDocument().XZ_Plane, [''])
	App.activeDocument().Sketch.MapMode = 'FlatFace'

	# sketch outer square
	geoList = []
	geoList.append(Part.LineSegment(App.Vector(-outer_x,-outer_y,0),App.Vector(outer_x,-outer_y,0)))  # bottom edge
	geoList.append(Part.LineSegment(App.Vector(outer_x,-outer_y,0),App.Vector(outer_x,outer_y,0)))  # right edge
	geoList.append(Part.LineSegment(App.Vector(outer_x,outer_y,0),App.Vector(-outer_x,outer_y,0)))  # top edge
	geoList.append(Part.LineSegment(App.Vector(-outer_x,outer_y,0),App.Vector(-outer_x,-outer_y,0)))  # left edge
	App.ActiveDocument.Sketch.addGeometry(geoList,False)

	# constraints needed for fillet anchors
	conList = []
	conList.append(Sketcher.Constraint('Coincident',0,2,1,1))
	conList.append(Sketcher.Constraint('Coincident',1,2,2,1))
	conList.append(Sketcher.Constraint('Coincident',2,2,3,1))
	conList.append(Sketcher.Constraint('Coincident',3,2,0,1))
	conList.append(Sketcher.Constraint('Horizontal',0))
	conList.append(Sketcher.Constraint('Horizontal',2))
	conList.append(Sketcher.Constraint('Vertical',1))
	conList.append(Sketcher.Constraint('Vertical',3))
	App.ActiveDocument.Sketch.addConstraint(conList)

	# sketch inner square
	geoList = []
	geoList.append(Part.LineSegment(App.Vector(-inner_x,-inner_y,0),App.Vector(inner_x,-inner_y,0)))
	geoList.append(Part.LineSegment(App.Vector(inner_x,-inner_y,0),App.Vector(inner_x,inner_y,0)))
	geoList.append(Part.LineSegment(App.Vector(inner_x,inner_y,0),App.Vector(-inner_x,inner_y,0)))
	geoList.append(Part.LineSegment(App.Vector(-inner_x,inner_y,0),App.Vector(-inner_x,-inner_y,0)))
	App.ActiveDocument.Sketch.addGeometry(geoList,False)

	# constraints for fillets
	conList = []
	conList.append(Sketcher.Constraint('Coincident',4,2,5,1))
	conList.append(Sketcher.Constraint('Coincident',5,2,6,1))
	conList.append(Sketcher.Constraint('Coincident',6,2,7,1))
	conList.append(Sketcher.Constraint('Coincident',7,2,4,1))
	conList.append(Sketcher.Constraint('Horizontal',4))
	conList.append(Sketcher.Constraint('Horizontal',6))
	conList.append(Sketcher.Constraint('Vertical',5))
	conList.append(Sketcher.Constraint('Vertical',7))
	App.ActiveDocument.Sketch.addConstraint(conList)

	# fillet squares
	if cradius != 0:
		App.ActiveDocument.Sketch.fillet(6,2,cradius)
		App.ActiveDocument.Sketch.fillet(5,2,cradius)
		App.ActiveDocument.Sketch.fillet(4,2,cradius)
		App.ActiveDocument.Sketch.fillet(4,1,cradius)
		App.ActiveDocument.Sketch.fillet(2,2,cradius)
		App.ActiveDocument.Sketch.fillet(1,2,cradius)
		App.ActiveDocument.Sketch.fillet(0,2,cradius)
		App.ActiveDocument.Sketch.fillet(0,1,cradius)

	# consider end cuts (center-to-center) in length calculation
	if e1angle == 90:
		if e2angle == 90:
			length = length

		else:
			length = length + (side1 * math.tan(math.radians(math.radians(90 - e2angle))) / 2) # () is midpoint of endcut from top-axis

	elif e2angle == 90:
		length = length + (side1 * math.tan(math.radians(90 - e1angle)) / 2)

	else:
		length = length +  (side1 * math.tan(math.radians(90 - e1angle)) / 2) + (side1 * math.tan(math.radians(90 - e2angle)) / 2)

	# boss extrude the sketch
	App.activeDocument().Body.newObject("PartDesign::Pad","Pad")
	App.activeDocument().Pad.Profile = App.activeDocument().Sketch
	App.ActiveDocument.Pad.Length = length
	App.ActiveDocument.recompute()  # requires recompute after each feature

	# create sketches for end cuts
	App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch001') # front
	App.activeDocument().Sketch001.Support = (App.activeDocument().YZ_Plane, [''])
	App.activeDocument().Sketch001.MapMode = 'FlatFace'

	App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch003') # top
	App.activeDocument().Sketch003.Support = (App.activeDocument().XY_Plane, [''])
	App.activeDocument().Sketch003.MapMode = 'FlatFace'

	# determine location of end cuts
	y = side1 / 2
	x1 = -length
	x = -side1 / math.tan(math.radians(e2angle))
	x2 = x1 + (side1 / math.tan(math.radians(e1angle)))

	# sketch first end cut
	if e1cutside == 1 and e1angle != 90:
		App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(x1,-y,0),App.Vector(x2,y,0)),False)
		App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(x2,y,0),App.Vector(x1,y,0)),False)
		App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(x1,y,0),App.Vector(x1,-y,0)),False)

	elif e1cutside == 2 and e1angle!= 90:
		y = side1 / 2
		x1 = -length
		x = -side1 / math.tan(math.radians(e2angle))
		x2 = x1 + (side1 / math.tan(math.radians(e1angle)))

		App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(-y,x1,0),App.Vector(y,x2,0)),False)
		App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(y,x2,0),App.Vector(y,x1,0)),False)
		App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(y,x1,0),App.Vector(-y,x1,0)),False)

		App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket003")
		App.activeDocument().Pocket003.Profile = App.activeDocument().Sketch003
		App.ActiveDocument.Pocket003.Length = 1000
		App.ActiveDocument.Pocket003.Length2 = 1000
		App.ActiveDocument.Pocket003.Type = 4
		App.ActiveDocument.recompute()

	# Fix End2CutSide add 90 when 2
	if e2cutside == 2:
		roffset += 90



	# determine rotation of end cuts
	if roffset == 0:

		# sketch second end cut
		if e2angle != 90:
			App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(0,-y,0),App.Vector(x,y,0)),False)
			App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(x,y,0),App.Vector(0,y,0)),False)
			App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(0,y,0),App.Vector(0,-y,0)),False)

		# extrude cut the end cuts
		if e1angle != 90 or e2angle != 90:
			App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket")
			App.activeDocument().Pocket.Profile = App.activeDocument().Sketch001
			App.ActiveDocument.Pocket.Length = 1000
			App.ActiveDocument.Pocket.Length2 = 1000
			App.ActiveDocument.Pocket.Type = 4
			App.ActiveDocument.recompute()

	elif roffset == 90:

		# extrude cut the first end cut
		if e1angle != 90 and e1cutside == 1:
			App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket")
			App.activeDocument().Pocket.Profile = App.activeDocument().Sketch001
			App.ActiveDocument.Pocket.Length = 1000
			App.ActiveDocument.Pocket.Length2 = 1000
			App.ActiveDocument.Pocket.Type = 4
			App.ActiveDocument.recompute()

		# adjust for roffset
		x = side2 / 2
		x1 = -length
		x2 = x1 - x
		y = -side2 / math.tan(math.radians(e2angle))

		if e2angle != 90:
			# create sketch for second end cut
			App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch002')
			App.activeDocument().Sketch002.Support = (App.activeDocument().XY_Plane, [''])
			App.activeDocument().Sketch002.MapMode = 'FlatFace'

			# sketch second end cut
			App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(-x,0,0),App.Vector(-x,y,0)),False)
			App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(-x,y,0),App.Vector(x,0,0)),False)
			App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(x,0,0),App.Vector(-x,0,0)),False)

			# extrude cut the second end cut
			App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket001")
			App.activeDocument().Pocket001.Profile = App.activeDocument().Sketch002
			App.ActiveDocument.Pocket001.Length = 1000
			App.ActiveDocument.Pocket001.Length2 = 1000
			App.ActiveDocument.Pocket001.Type = 4
			App.ActiveDocument.recompute()

	elif roffset == 180:  # parallel

		if e2angle != 90:

			# sketch second end cut
			App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(x,-y,0),App.Vector(0,y,0)),False)
			App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(0,y,0),App.Vector(0,-y,0)),False)
			App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(0,-y,0),App.Vector(x,-y,0)),False)

			# extrude cut both end cuts
			App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket")
			App.activeDocument().Pocket.Profile = App.activeDocument().Sketch001
			App.ActiveDocument.Pocket.Length = 1000
			App.ActiveDocument.Pocket.Length2 = 1000
			App.ActiveDocument.Pocket.Type = 4
			App.ActiveDocument.recompute()

	elif roffset == 270:

		# extrude cut the first end cut
		if e1angle != 90 and e1cutside == 1:
			App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket")
			App.activeDocument().Pocket.Profile = App.activeDocument().Sketch001
			App.ActiveDocument.Pocket.Length = side2
			App.ActiveDocument.Pocket.Length2 = side2
			App.ActiveDocument.Pocket.Type = 4
			App.ActiveDocument.recompute()

		# adjust for roffset
		x = side2 / 2
		x1 = -length
		x2 = x1 - x
		y = -side2 / math.tan(math.radians(e2angle))

		if e2angle != 90:

			# create sketch for second end cut
			App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch002')
			App.activeDocument().Sketch002.Support = (App.activeDocument().XY_Plane, [''])
			App.activeDocument().Sketch002.MapMode = 'FlatFace'

			# sketch second end cut
			App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(x,0,0),App.Vector(x,y,0)),False)
			App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(x,y,0),App.Vector(-x,0,0)),False)
			App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(-x,0,0),App.Vector(x,0,0)),False)

			# extrude cut the second end cut
			App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket001")
			App.activeDocument().Pocket001.Profile = App.activeDocument().Sketch002
			App.ActiveDocument.Pocket001.Length = 1000
			App.ActiveDocument.Pocket001.Length2 = 1000
			App.ActiveDocument.Pocket001.Type = 4
			App.ActiveDocument.recompute()


	# rotate tube to fit horizontally in PieceMaker window
	App.getDocument("RectangularTube").Body.Placement=App.Placement(App.Vector(0,0,0), App.Rotation(90,0,0), App.Vector(0,0,0))

	# render and save STL file
	global __objs__
	__objs__=[]
	__objs__.append(FreeCAD.getDocument("RectangularTube").getObject("Body"))

# generate angle iron tube STL file
def angle_iron_tube(side1, side2, wall, cradius, length, roffset, e1angle, e2angle, e1cutside, e2cutside):

	if e1angle < 0:
		e1angle = 360 - e1angle
	if e2angle < 0:
		e2angle = 360 - e2angle

	# calculate positions of corners for square face
	outer_x = 0.5 * side1
	outer_y = 0.5 * side2

	inner_x = outer_x - wall
	inner_y = outer_y - wall

	# create new part with the PartDesign workbench
	App.newDocument("AngleIronTube")
	App.activeDocument().addObject('PartDesign::Body','Body')

	# create sketch on the front plane
	App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch')
	App.activeDocument().Sketch.Support = (App.activeDocument().XZ_Plane, [''])
	App.activeDocument().Sketch.MapMode = 'FlatFace'

	# sketch outer square
	geoList = []
	geoList.append(Part.LineSegment(App.Vector(-outer_x,-outer_y,0),App.Vector(outer_x,-outer_y,0)))  # bottom edge
	geoList.append(Part.LineSegment(App.Vector(outer_x,-outer_y,0),App.Vector(outer_x,outer_y,0)))  # right edge
	geoList.append(Part.LineSegment(App.Vector(outer_x,outer_y,0),App.Vector(-outer_x,outer_y,0)))  # top edge
	geoList.append(Part.LineSegment(App.Vector(-outer_x,outer_y,0),App.Vector(-outer_x,-outer_y,0)))  # left edge
	App.ActiveDocument.Sketch.addGeometry(geoList,False)

	# constraints needed for fillet anchors
	conList = []
	conList.append(Sketcher.Constraint('Coincident',0,2,1,1))
	conList.append(Sketcher.Constraint('Coincident',1,2,2,1))
	conList.append(Sketcher.Constraint('Coincident',2,2,3,1))
	conList.append(Sketcher.Constraint('Coincident',3,2,0,1))
	conList.append(Sketcher.Constraint('Horizontal',0))
	conList.append(Sketcher.Constraint('Horizontal',2))
	conList.append(Sketcher.Constraint('Vertical',1))
	conList.append(Sketcher.Constraint('Vertical',3))
	App.ActiveDocument.Sketch.addConstraint(conList)

	# sketch inner square
	geoList = []
	geoList.append(Part.LineSegment(App.Vector(-inner_x,-inner_y,0),App.Vector(inner_x,-inner_y,0)))
	geoList.append(Part.LineSegment(App.Vector(inner_x,-inner_y,0),App.Vector(inner_x,inner_y,0)))
	geoList.append(Part.LineSegment(App.Vector(inner_x,inner_y,0),App.Vector(-inner_x,inner_y,0)))
	geoList.append(Part.LineSegment(App.Vector(-inner_x,inner_y,0),App.Vector(-inner_x,-inner_y,0)))
	App.ActiveDocument.Sketch.addGeometry(geoList,False)

	# constraints for fillets
	conList = []
	conList.append(Sketcher.Constraint('Coincident',4,2,5,1))
	conList.append(Sketcher.Constraint('Coincident',5,2,6,1))
	conList.append(Sketcher.Constraint('Coincident',6,2,7,1))
	conList.append(Sketcher.Constraint('Coincident',7,2,4,1))
	conList.append(Sketcher.Constraint('Horizontal',4))
	conList.append(Sketcher.Constraint('Horizontal',6))
	conList.append(Sketcher.Constraint('Vertical',5))
	conList.append(Sketcher.Constraint('Vertical',7))
	App.ActiveDocument.Sketch.addConstraint(conList)

	# consider end cuts (center-to-center) in length calculation
	if e1angle == 90:
		if e2angle == 90:
			length = length

		else:
			length = length + (side1 * math.tan(math.radians(90 - e2angle)) / 2) # () is midpoint of endcut from top-axis

	elif e2angle == 90:
		length = length + (side1 * math.tan(math.radians(90 - e1angle)) / 2)

	else:
		length = length +  (side1 * math.tan(math.radians(90 - e1angle)) / 2) + (side1 * math.tan(math.radians(90 - e2angle)) / 2)

	# boss extrude the sketch
	App.activeDocument().Body.newObject("PartDesign::Pad","Pad")
	App.activeDocument().Pad.Profile = App.activeDocument().Sketch
	App.ActiveDocument.Pad.Length = length
	App.ActiveDocument.recompute()  # requires recompute after each feature

	# create sketch on the front plane to cut angle iron shape
	App.activeDocument().Body.newObject('Sketcher::SketchObject','SketchAngleIronCut')
	App.activeDocument().SketchAngleIronCut.Support = (App.activeDocument().XZ_Plane, [''])
	App.activeDocument().SketchAngleIronCut.MapMode = 'FlatFace'

	# sketch square to be removed
	geoList = []
	geoList.append(Part.LineSegment(App.Vector(-inner_x,-inner_y,0),App.Vector(outer_x,-inner_y,0)))  # bottom edge
	geoList.append(Part.LineSegment(App.Vector(outer_x,-inner_y,0),App.Vector(outer_x,outer_y,0)))  # right edge
	geoList.append(Part.LineSegment(App.Vector(outer_x,outer_y,0),App.Vector(-inner_x,outer_y,0)))  # top edge
	geoList.append(Part.LineSegment(App.Vector(-inner_x,outer_y,0),App.Vector(-inner_x,-inner_y,0)))  # left edge
	App.ActiveDocument.SketchAngleIronCut.addGeometry(geoList,False)

	# extrude cut the square
	App.activeDocument().Body.newObject("PartDesign::Pocket","PocketAngleIronCut")
	App.activeDocument().PocketAngleIronCut.Profile = App.activeDocument().SketchAngleIronCut
	App.ActiveDocument.PocketAngleIronCut.Length = 1000000000 # measured in mm, excessively high to account for any sized length
	App.ActiveDocument.PocketAngleIronCut.Length2 = 1000000000
	App.ActiveDocument.PocketAngleIronCut.Type = 4
	App.ActiveDocument.recompute()

	#Note:  Filleting the edges isn't working at the moment, will uncomment when it is fixed
	# fillet edges
	#App.getDocument('AngleIronTube').getObject('Body').newObject('PartDesign::Fillet','Fillet')
	#App.getDocument('AngleIronTube').getObject('Fillet').Radius = cradius * 0.8 # passed value of cradius too large
	#App.getDocument('AngleIronTube').getObject('Fillet').Base = (App.getDocument('AngleIronTube').getObject('PocketAngleIronCut'),["Edge21","Edge9","Edge24"])
	#App.getDocument('AngleIronTube').recompute()

	# create sketches for end cuts
	App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch001') # front
	App.activeDocument().Sketch001.Support = (App.activeDocument().YZ_Plane, [''])
	App.activeDocument().Sketch001.MapMode = 'FlatFace'

	App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch003') # top
	App.activeDocument().Sketch003.Support = (App.activeDocument().XY_Plane, [''])
	App.activeDocument().Sketch003.MapMode = 'FlatFace'

	# determine location of end cuts
	y = side1 / 2
	x1 = -length
	if e1angle < 0:
		e1angle = 360 - e1angle
	if e2angle < 0:
		e2angle = 360 - e2angle
	x = -side1 / math.tan(math.radians(e2angle))
	x2 = x1 + (side1 / math.tan(math.radians(e1angle)))

	# sketch first end cut
	if e1cutside == 1 and e1angle != 90:
		App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(x1,-y,0),App.Vector(x2,y,0)),False)
		App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(x2,y,0),App.Vector(x1,y,0)),False)
		App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(x1,y,0),App.Vector(x1,-y,0)),False)

		App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket003")
		App.activeDocument().Pocket003.Profile = App.activeDocument().Sketch001
		App.ActiveDocument.Pocket003.Length = 1000
		App.ActiveDocument.Pocket003.Length2 = 1000
		App.ActiveDocument.Pocket003.Type = 4
		App.ActiveDocument.recompute()

	elif e1cutside == 2 and e1angle != 90:

		App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(-y,x1,0),App.Vector(y,x2,0)),False)
		App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(y,x2,0),App.Vector(y,x1,0)),False)
		App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(y,x1,0),App.Vector(-y,x1,0)),False)

		App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket003")
		App.activeDocument().Pocket003.Profile = App.activeDocument().Sketch003
		App.ActiveDocument.Pocket003.Length = 1000
		App.ActiveDocument.Pocket003.Length2 = 1000
		App.ActiveDocument.Pocket003.Type = 4
		App.ActiveDocument.recompute()


	# determine rotation of end cuts
	if roffset == 0:

		# sketch second end cut
		if e2angle != 90:
			App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(0,-y,0),App.Vector(x,y,0)),False)
			App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(x,y,0),App.Vector(0,y,0)),False)
			App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(0,y,0),App.Vector(0,-y,0)),False)


			App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket")
			App.activeDocument().Pocket.Profile = App.activeDocument().Sketch001
			App.ActiveDocument.Pocket.Length = 1000
			App.ActiveDocument.Pocket.Length2 = 1000
			App.ActiveDocument.Pocket.Type = 4
			App.ActiveDocument.recompute()

	elif roffset == 90:



		# adjust for roffset
		#x = side2 / 2
		#x1 = -length
		#x2 = x1 - x
		#y = -side2 / math.tan(math.radians(e2angle))


		if e2angle != 90:
			# create sketch for second end cut
			#App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch002')
			#App.activeDocument().Sketch002.Support = (App.activeDocument().XY_Plane, [''])
			#App.activeDocument().Sketch002.MapMode = 'FlatFace'

			# sketch second end cut
			#App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(-x,0,0),App.Vector(-x,y,0)),False)
			#App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(-x,y,0),App.Vector(x,0,0)),False)
			#App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(x,0,0),App.Vector(-x,0,0)),False)

			App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(-y,0,0),App.Vector(y,x,0)),False)
			App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(y,x,0),App.Vector(y,0,0)),False)
			App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(y,0,0),App.Vector(-y,0,0)),False)

			# extrude cut the second end cut
			App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket001")
			App.activeDocument().Pocket001.Profile = App.activeDocument().Sketch003
			App.ActiveDocument.Pocket001.Length = 1000
			App.ActiveDocument.Pocket001.Length2 = 1000
			App.ActiveDocument.Pocket001.Type = 4
			App.ActiveDocument.recompute()

	elif roffset == 180:  # parallel

		if e2angle != 90:

			# sketch second end cut
			App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(x,-y,0),App.Vector(0,y,0)),False)
			App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(0,y,0),App.Vector(0,-y,0)),False)
			App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(0,-y,0),App.Vector(x,-y,0)),False)

			# extrude cut both end cuts
			App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket")
			App.activeDocument().Pocket.Profile = App.activeDocument().Sketch001
			App.ActiveDocument.Pocket.Length = 1000
			App.ActiveDocument.Pocket.Length2 = 1000
			App.ActiveDocument.Pocket.Type = 4
			App.ActiveDocument.recompute()

	elif roffset == 270:

		# extrude cut the first end cut
		if e1angle != 90 and e1cutside == 1:
			App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket")
			App.activeDocument().Pocket.Profile = App.activeDocument().Sketch001
			App.ActiveDocument.Pocket.Length = side2
			App.ActiveDocument.Pocket.Length2 = side2
			App.ActiveDocument.Pocket.Type = 4
			App.ActiveDocument.recompute()

		# adjust for roffset
		x = side2 / 2
		x1 = -length
		x2 = x1 - x
		y = -side2 / math.tan(math.radians(e2angle))

		if e2angle != 90:

			# create sketch for second end cut
			App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch002')
			App.activeDocument().Sketch002.Support = (App.activeDocument().XY_Plane, [''])
			App.activeDocument().Sketch002.MapMode = 'FlatFace'

			# sketch second end cut
			App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(x,0,0),App.Vector(x,y,0)),False)
			App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(x,y,0),App.Vector(-x,0,0)),False)
			App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(-x,0,0),App.Vector(x,0,0)),False)

			# extrude cut the second end cut
			App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket001")
			App.activeDocument().Pocket001.Profile = App.activeDocument().Sketch002
			App.ActiveDocument.Pocket001.Length = 1000
			App.ActiveDocument.Pocket001.Length2 = 1000
			App.ActiveDocument.Pocket001.Type = 4
			App.ActiveDocument.recompute()

	# rotate tube to fit horizontally in PieceMaker window
	App.getDocument("AngleIronTube").Body.Placement=App.Placement(App.Vector(0,0,0), App.Rotation(90,0,0), App.Vector(0,0,0))


	# render and save STL file
	global __objs__
	__objs__=[]
	__objs__.append(FreeCAD.getDocument("AngleIronTube").getObject("Body"))




# generate flat bar tube STL file
def flat_bar_tube(side1, side2, wall, cradius, length, roffset, e1angle, e2angle, e1cutside, e2cutside):

	if e1angle < 0:
		e1angle = 360 - e1angle
	if e2angle < 0:
		e2angle = 360 - e2angle

	# calculate positions of corners for square face
	outer_x = 0.5 * side2
	outer_y = 0.5 * side1

	inner_x = outer_x - wall
	inner_y = outer_y - wall

	# create new part with the PartDesign workbench
	App.newDocument("FlatBarTube")
	App.activeDocument().addObject('PartDesign::Body','Body')

	# create sketch on the front plane
	App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch')
	App.activeDocument().Sketch.Support = (App.activeDocument().XZ_Plane, [''])
	App.activeDocument().Sketch.MapMode = 'FlatFace'

	# sketch outer square
	geoList = []
	geoList.append(Part.LineSegment(App.Vector(-outer_x,-outer_y,0),App.Vector(outer_x,-outer_y,0)))  # bottom edge
	geoList.append(Part.LineSegment(App.Vector(outer_x,-outer_y,0),App.Vector(outer_x,outer_y,0)))  # right edge
	geoList.append(Part.LineSegment(App.Vector(outer_x,outer_y,0),App.Vector(-outer_x,outer_y,0)))  # top edge
	geoList.append(Part.LineSegment(App.Vector(-outer_x,outer_y,0),App.Vector(-outer_x,-outer_y,0)))  # left edge
	App.ActiveDocument.Sketch.addGeometry(geoList,False)

	# consider end cuts (center-to-center) in length calculation
	if e1angle == 90:
		if e2angle == 90:
			length = length

		else:
			length = length + (side1 * math.tan(math.radians(90 - e2angle)) / 2) # () is midpoint of endcut from top-axis

	elif e2angle == 90:
		length = length + (side1 * math.tan(math.radians(90 - e1angle)) / 2)

	else:
		length = length +  (side1 * math.tan(math.radians(90 - e1angle)) / 2) + (side1 * math.tan(math.radians(90 - e2angle)) / 2)

	# boss extrude the sketch
	App.activeDocument().Body.newObject("PartDesign::Pad","Pad")
	App.activeDocument().Pad.Profile = App.activeDocument().Sketch
	App.ActiveDocument.Pad.Length = length
	App.ActiveDocument.recompute()  # requires recompute after each feature

	# create sketch on the front plane to cut flat bar shape
	App.activeDocument().Body.newObject('Sketcher::SketchObject','SketchFlatBarCut')
	App.activeDocument().SketchFlatBarCut.Support = (App.activeDocument().XZ_Plane, [''])
	App.activeDocument().SketchFlatBarCut.MapMode = 'FlatFace'

	# sketch square to be removed
	geoList = []
	geoList.append(Part.LineSegment(App.Vector(-outer_x,-inner_y,0),App.Vector(outer_x,-inner_y,0)))  # bottom edge
	geoList.append(Part.LineSegment(App.Vector(outer_x,-inner_y,0),App.Vector(outer_x,outer_y,0)))  # right edge
	geoList.append(Part.LineSegment(App.Vector(outer_x,outer_y,0),App.Vector(-outer_x,outer_y,0)))  # top edge
	geoList.append(Part.LineSegment(App.Vector(-outer_x,outer_y,0),App.Vector(-outer_x,-inner_y,0)))  # left edge
	App.ActiveDocument.SketchFlatBarCut.addGeometry(geoList,False)

	# extrude cut the square
	App.activeDocument().Body.newObject("PartDesign::Pocket","PocketFlatBarCut")
	App.activeDocument().PocketFlatBarCut.Profile = App.activeDocument().SketchFlatBarCut
	App.ActiveDocument.PocketFlatBarCut.Length = 1000000000 # measured in mm, excessively high to account for any sized length
	App.ActiveDocument.PocketFlatBarCut.Length2 = 1000000000
	App.ActiveDocument.PocketFlatBarCut.Type = 4
	App.ActiveDocument.recompute()

	# create sketches for end cuts
	App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch001') # front
	App.activeDocument().Sketch001.Support = (App.activeDocument().XY_Plane, [''])
	App.activeDocument().Sketch001.MapMode = 'FlatFace'



	# determine location of end cuts
	y = side1 / 2
	x1 = -length
	if e1angle < 0:
		e1angle = 360 - e1angle
	if e2angle < 0:
		e2angle = 360 - e2angle
	x = -side1 / math.tan(math.radians(e2angle))
	x2 = x1 + (side1 / math.tan(math.radians(e1angle)))

	geoList = []
	# sketch first end cut
	if e1angle != 90 and e1angle != 90:

##                geoList.append(Part.LineSegment(App.Vector(x1,-y,0),App.Vector(x2,y,0)))
##                geoList.append(Part.LineSegment(App.Vector(x2,y,0),App.Vector(x1,y,0)))
##                geoList.append(Part.LineSegment(App.Vector(x1,y,0),App.Vector(x1,-y,0)))

		geoList.append(Part.LineSegment(App.Vector(-y,x1,0),App.Vector(y,x2,0)))
		geoList.append(Part.LineSegment(App.Vector(y,x2,0),App.Vector(y,x1,0)))
		geoList.append(Part.LineSegment(App.Vector(y,x1,0),App.Vector(-y,x1,0)))

		App.ActiveDocument.Sketch001.addGeometry(geoList, False)

	# determine rotation of end cuts
	if roffset == 0:

		# sketch second end cut
		if e2angle != 90:
			geoList = []

##                        geoList.append(Part.LineSegment(App.Vector(0,-y,0),App.Vector(x,y,0)))
##                        geoList.append(Part.LineSegment(App.Vector(x,y,0),App.Vector(0,y,0)))
##                        geoList.append(Part.LineSegment(App.Vector(0,y,0),App.Vector(0,-y,0)))

			geoList.append(Part.LineSegment(App.Vector(-y,0,0),App.Vector(y,x,0)))
			geoList.append(Part.LineSegment(App.Vector(y,x,0),App.Vector(y,0,0)))
			geoList.append(Part.LineSegment(App.Vector(y,0,0),App.Vector(-y,0,0)))

			App.ActiveDocument.Sketch001.addGeometry(geoList, False)

		# extrude cut the end cuts
		if e1angle != 90 or e2angle != 90:
			#App.ActiveDocument.Sketch001.addGeometry(geoList, False)
			App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket")
			App.activeDocument().Pocket.Profile = App.activeDocument().Sketch001
			App.ActiveDocument.Pocket.Length = 1000
			App.ActiveDocument.Pocket.Length2 = 1000
			App.ActiveDocument.Pocket.Type = 4
			App.ActiveDocument.recompute()

	elif roffset == 180:  # parallel

		if e2angle != 90:
			geoList = []

			# sketch second end cut
##                        App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(x,-y,0),App.Vector(0,y,0)),False)
##                        App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(0,y,0),App.Vector(0,-y,0)),False)
##                        App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(0,-y,0),App.Vector(x,-y,0)),False)

			App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(-y,x,0),App.Vector(y,0,0)),False)
			App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(y,0,0),App.Vector(-y,0,0)),False)
			App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(-y,0,0),App.Vector(-y,x,0)),False)

		# extrude cut both end cuts
		if e1angle != 90 or e2angle != 90:
			App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket")
			App.activeDocument().Pocket.Profile = App.activeDocument().Sketch001
			App.ActiveDocument.Pocket.Length = 1000
			App.ActiveDocument.Pocket.Length2 = 1000
			App.ActiveDocument.Pocket.Type = 4
			App.ActiveDocument.recompute()


	# rotate tube to fit horizontally in PieceMaker window
	App.getDocument("FlatBarTube").Body.Placement=App.Placement(App.Vector(0,0,0), App.Rotation(90,0,0), App.Vector(0,0,0))

	# render and save STL file
	global __objs__
	__objs__=[]
	__objs__.append(FreeCAD.getDocument("FlatBarTube").getObject("Body"))



# generate angle iron tube STL file
def c_channel_tube(side1, side2, wall, cradius, length, roffset, e1angle, e2angle, e1cutside, e2cutside):


	if e1angle < 0:
		e1angle = 360 - e1angle
	if e2angle < 0:
		e2angle = 360 - e2angle

	# calculate positions of corners for square face
	outer_x = 0.5 * side1
	outer_y = 0.5 * side2

	inner_x = outer_x - wall
	inner_y = outer_y - wall

	# create new part with the PartDesign workbench
	App.newDocument("CChannelTube")
	App.activeDocument().addObject('PartDesign::Body','Body')

	# create sketch on the front plane
	App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch')
	App.activeDocument().Sketch.Support = (App.activeDocument().XZ_Plane, [''])
	App.activeDocument().Sketch.MapMode = 'FlatFace'

	# sketch outer square
	geoList = []
	geoList.append(Part.LineSegment(App.Vector(-outer_x,-outer_y,0),App.Vector(outer_x,-outer_y,0)))  # bottom edge
	geoList.append(Part.LineSegment(App.Vector(outer_x,-outer_y,0),App.Vector(outer_x,outer_y,0)))  # right edge
	geoList.append(Part.LineSegment(App.Vector(outer_x,outer_y,0),App.Vector(-outer_x,outer_y,0)))  # top edge
	geoList.append(Part.LineSegment(App.Vector(-outer_x,outer_y,0),App.Vector(-outer_x,-outer_y,0)))  # left edge
	App.ActiveDocument.Sketch.addGeometry(geoList,False)

##	# constraints needed for fillet anchors
##	conList = []
##	conList.append(Sketcher.Constraint('Coincident',0,2,1,1))
##	conList.append(Sketcher.Constraint('Coincident',1,2,2,1))
##	conList.append(Sketcher.Constraint('Coincident',2,2,3,1))
##	conList.append(Sketcher.Constraint('Coincident',3,2,0,1))
##	conList.append(Sketcher.Constraint('Horizontal',0))
##	conList.append(Sketcher.Constraint('Horizontal',2))
##	conList.append(Sketcher.Constraint('Vertical',1))
##	conList.append(Sketcher.Constraint('Vertical',3))
##	App.ActiveDocument.Sketch.addConstraint(conList)

	# sketch inner square
	geoList = []
	geoList.append(Part.LineSegment(App.Vector(-inner_x,-inner_y,0),App.Vector(inner_x,-inner_y,0)))
	geoList.append(Part.LineSegment(App.Vector(inner_x,-inner_y,0),App.Vector(inner_x,inner_y,0)))
	geoList.append(Part.LineSegment(App.Vector(inner_x,inner_y,0),App.Vector(-inner_x,inner_y,0)))
	geoList.append(Part.LineSegment(App.Vector(-inner_x,inner_y,0),App.Vector(-inner_x,-inner_y,0)))
	App.ActiveDocument.Sketch.addGeometry(geoList,False)

##	# constraints for fillets
##	conList = []
##	conList.append(Sketcher.Constraint('Coincident',4,2,5,1))
##	conList.append(Sketcher.Constraint('Coincident',5,2,6,1))
##	conList.append(Sketcher.Constraint('Coincident',6,2,7,1))
##	conList.append(Sketcher.Constraint('Coincident',7,2,4,1))
##	conList.append(Sketcher.Constraint('Horizontal',4))
##	conList.append(Sketcher.Constraint('Horizontal',6))
##	conList.append(Sketcher.Constraint('Vertical',5))
##	conList.append(Sketcher.Constraint('Vertical',7))
##	App.ActiveDocument.Sketch.addConstraint(conList)

	# consider end cuts (center-to-center) in length calculation
	if e1angle == 90:
		if e2angle == 90:
			length = length

		else:
			length = length + (side1 * math.tan(math.radians(90 - e2angle)) / 2) # () is midpoint of endcut from top-axis

	elif e2angle == 90:
		length = length + (side1 * math.tan(math.radians(90 - e1angle)) / 2)

	else:
		length = length +  (side1 * math.tan(math.radians(90 - e1angle)) / 2) + (side1 * math.tan(math.radians(90 - e2angle)) / 2)

	# boss extrude the sketch
	App.activeDocument().Body.newObject("PartDesign::Pad","Pad")
	App.activeDocument().Pad.Profile = App.activeDocument().Sketch
	App.ActiveDocument.Pad.Length = length
	App.ActiveDocument.recompute()  # requires recompute after each feature

	# create sketch on the front plane to cut angle iron shape
	App.activeDocument().Body.newObject('Sketcher::SketchObject','SketchCChannelCut')
	App.activeDocument().SketchCChannelCut.Support = (App.activeDocument().XZ_Plane, [''])
	App.activeDocument().SketchCChannelCut.MapMode = 'FlatFace'

	# sketch square to be removed
	geoList = []
	geoList.append(Part.LineSegment(App.Vector(-inner_x,-inner_y,0),App.Vector(inner_x,-inner_y,0)))  # bottom edge
	geoList.append(Part.LineSegment(App.Vector(inner_x,-inner_y,0),App.Vector(inner_x,outer_y,0)))  # right edge
	geoList.append(Part.LineSegment(App.Vector(inner_x,outer_y,0),App.Vector(-inner_x,outer_y,0)))  # top edge
	geoList.append(Part.LineSegment(App.Vector(-inner_x,outer_y,0),App.Vector(-inner_x,-inner_y,0)))  # left edge
	App.ActiveDocument.SketchCChannelCut.addGeometry(geoList,False)

	# extrude cut the square
	App.activeDocument().Body.newObject("PartDesign::Pocket","PocketCChannelCut")
	App.activeDocument().PocketCChannelCut.Profile = App.activeDocument().SketchCChannelCut
	App.ActiveDocument.PocketCChannelCut.Length = 1000000000 # measured in mm, excessively high to account for any sized length
	App.ActiveDocument.PocketCChannelCut.Length2 = 1000000000
	App.ActiveDocument.PocketCChannelCut.Type = 4
	App.ActiveDocument.recompute()

##	# fillet edges
##	App.getDocument('CChannelTube').getObject('Body').newObject('PartDesign::Fillet','Fillet')
##	App.getDocument('CChannelTube').getObject('Fillet').Radius = cradius * 0.8 # passed value of cradius too large
##	App.getDocument('CChannelTube').getObject('Fillet').Base = (App.getDocument('CChannelTube').getObject('PocketCChannelCut'),["Edge21","Edge9","Edge24"])
##	App.getDocument('CChannelTube').recompute()

	# create sketches for end cuts
	App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch001') # front
	App.activeDocument().Sketch001.Support = (App.activeDocument().YZ_Plane, [''])
	App.activeDocument().Sketch001.MapMode = 'FlatFace'

	App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch003') # top
	App.activeDocument().Sketch003.Support = (App.activeDocument().XY_Plane, [''])
	App.activeDocument().Sketch003.MapMode = 'FlatFace'

	# determine location of end cuts
	y = side1 / 2
	x1 = -length
	if e1angle < 0:
		e1angle = 360 - e1angle
	if e2angle < 0:
		e2angle = 360 - e2angle
	x = -side1 / math.tan(math.radians(e2angle))
	x2 = x1 + (side1 / math.tan(math.radians(e1angle)))

	# sketch first end cut
	if e1cutside == 1 and e1angle != 90:
		App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(x1,-y,0),App.Vector(x2,y,0)),False)
		App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(x2,y,0),App.Vector(x1,y,0)),False)
		App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(x1,y,0),App.Vector(x1,-y,0)),False)

		App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket003")
		App.activeDocument().Pocket003.Profile = App.activeDocument().Sketch001
		App.ActiveDocument.Pocket003.Length = 1000
		App.ActiveDocument.Pocket003.Length2 = 1000
		App.ActiveDocument.Pocket003.Type = 4
		App.ActiveDocument.recompute()

	elif e1cutside == 2 and e1angle != 90:
		y = side1 / 2
		x1 = -length
		x = -side1 / math.tan(math.radians(e2angle))
		x2 = x1 + (side1 / math.tan(math.radians(e1angle)))

		App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(-y,x1,0),App.Vector(y,x2,0)),False)
		App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(y,x2,0),App.Vector(y,x1,0)),False)
		App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(y,x1,0),App.Vector(-y,x1,0)),False)

		App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket003")
		App.activeDocument().Pocket003.Profile = App.activeDocument().Sketch003
		App.ActiveDocument.Pocket003.Length = 1000
		App.ActiveDocument.Pocket003.Length2 = 1000
		App.ActiveDocument.Pocket003.Type = 4
		App.ActiveDocument.recompute()

	##filename = os.path.dirname(os.path.abspath(__file__))
	##filename.replace("//","/")
	##filename += "/Test1.FCStd"
	##App.ActiveDocument.saveAs(filename)
	##App.closeDocument("CChannelTube")
	##FreeCAD.openDocument(filename)

	# determine rotation of end cuts
	if roffset == 0:

		# sketch second end cut
		if e2angle != 90:

			if e2cutside == 1:
				App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(0,-y,0),App.Vector(x,y,0)),False)
				App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(x,y,0),App.Vector(0,y,0)),False)
				App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(0,y,0),App.Vector(0,-y,0)),False)

				# extrude cut the end cuts
				App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket002")
				App.activeDocument().Pocket002.Profile = App.activeDocument().Sketch001
				App.ActiveDocument.Pocket002.Length = 1000
				App.ActiveDocument.Pocket002.Length2 = 1000
				App.ActiveDocument.Pocket002.Type = 4
				App.ActiveDocument.recompute()

			elif e2cutside == 2:
				App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(-y,0,0),App.Vector(y,x,0)),False)
				App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(y,x,0),App.Vector(y,0,0)),False)
				App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(y,0,0),App.Vector(-y,0,0)),False)

				# extrude cut the end cuts
				App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket002")
				App.activeDocument().Pocket002.Profile = App.activeDocument().Sketch003
				App.ActiveDocument.Pocket002.Length = 1000
				App.ActiveDocument.Pocket002.Length2 = 1000
				App.ActiveDocument.Pocket002.Type = 4
				App.ActiveDocument.recompute()

##	elif roffset == 90:
##
##		# extrude cut the first end cut
##		if e1angle != 90 and e1cutside == 1:
##			App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket")
##			App.activeDocument().Pocket.Profile = App.activeDocument().Sketch001
##			App.ActiveDocument.Pocket.Length = 1000
##			App.ActiveDocument.Pocket.Length2 = 1000
##			App.ActiveDocument.Pocket.Type = 4
##			App.ActiveDocument.recompute()
##
##		# adjust for roffset
##		x = side2 / 2
##		x1 = -length
##		x2 = x1 - x
##		y = -side2 / math.tan(math.radians(e2angle))
##
##		if e2angle != 90:
##			# create sketch for second end cut
##			App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch002')
##			App.activeDocument().Sketch002.Support = (App.activeDocument().XY_Plane, [''])
##			App.activeDocument().Sketch002.MapMode = 'FlatFace'
##
##			# sketch second end cut
##			App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(-x,0,0),App.Vector(-x,y,0)),False)
##			App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(-x,y,0),App.Vector(x,0,0)),False)
##			App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(x,0,0),App.Vector(-x,0,0)),False)
##
##			# extrude cut the second end cut
##			App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket001")
##			App.activeDocument().Pocket001.Profile = App.activeDocument().Sketch002
##			App.ActiveDocument.Pocket001.Length = 1000
##			App.ActiveDocument.Pocket001.Length2 = 1000
##			App.ActiveDocument.Pocket001.Type = 4
##			App.ActiveDocument.recompute()

	elif roffset == 180:  # parallel

		if e2angle != 90:

			# sketch second end cut
			if e2cutside == 1:
				App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(x,-y,0),App.Vector(0,y,0)),False)
				App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(0,y,0),App.Vector(0,-y,0)),False)
				App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(0,-y,0),App.Vector(x,-y,0)),False)

				# extrude cut the end cuts
				App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket002")
				App.activeDocument().Pocket002.Profile = App.activeDocument().Sketch001
				App.ActiveDocument.Pocket002.Length = 1000
				App.ActiveDocument.Pocket002.Length2 = 1000
				App.ActiveDocument.Pocket002.Type = 4
				App.ActiveDocument.recompute()

			elif e2cutside == 2:
				App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(-y,x,0),App.Vector(y,0,0)),False)
				App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(y,0,0),App.Vector(-y,0,0)),False)
				App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(-y,0,0),App.Vector(-y,x,0)),False)

				# extrude cut the end cuts
				App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket004")
				App.activeDocument().Pocket004.Profile = App.activeDocument().Sketch003
				App.ActiveDocument.Pocket004.Length = 1000
				App.ActiveDocument.Pocket004.Length2 = 1000
				App.ActiveDocument.Pocket004.Type = 4
				App.ActiveDocument.recompute()

##	elif roffset == 270:
##
##		# extrude cut the first end cut
##		if e1angle != 90 and e1cutside == 1:
##			App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket")
##			App.activeDocument().Pocket.Profile = App.activeDocument().Sketch001
##			App.ActiveDocument.Pocket.Length = side2
##			App.ActiveDocument.Pocket.Length2 = side2
##			App.ActiveDocument.Pocket.Type = 4
##			App.ActiveDocument.recompute()
##
##		# adjust for roffset
##		x = side2 / 2
##		x1 = -length
##		x2 = x1 - x
##		y = -side2 / math.tan(math.radians(e2angle))
##
##		if e2angle != 90:
##
##			# create sketch for second end cut
##			App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch002')
##			App.activeDocument().Sketch002.Support = (App.activeDocument().XY_Plane, [''])
##			App.activeDocument().Sketch002.MapMode = 'FlatFace'
##
##			# sketch second end cut
##			App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(x,0,0),App.Vector(x,y,0)),False)
##			App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(x,y,0),App.Vector(-x,0,0)),False)
##			App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(-x,0,0),App.Vector(x,0,0)),False)
##
##			# extrude cut the second end cut
##			App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket001")
##			App.activeDocument().Pocket001.Profile = App.activeDocument().Sketch002
##			App.ActiveDocument.Pocket001.Length = 1000
##			App.ActiveDocument.Pocket001.Length2 = 1000
##			App.ActiveDocument.Pocket001.Type = 4
##			App.ActiveDocument.recompute()

	#App.ActiveDocument.save()

	# rotate tube to fit horizontally in PieceMaker window
	App.ActiveDocument.Body.Placement=App.Placement(App.Vector(0,0,0), App.Rotation(90,0,0), App.Vector(0,0,0))
	#App.getDocument(filename).Body.Placement=App.Placement(App.Vector(0,0,0), App.Rotation(90,0,0), App.Vector(0,0,0))

	# render and save STL file
	global __objs__
	__objs__=[]
	#__objs__.append(App.ActiveDocument.getObject("Body"))
	__objs__.append(FreeCAD.getDocument("CChannelTube").getObject("Body"))






# generate I-Beam tube STL file
def i_beam_tube(side1, side2, wall, cradius, length, roffset, e1angle, e2angle, e1cutside, e2cutside):


	while e1angle < 0:
		e1angle += 360
	while e2angle < 0:
		e2angle += 360

	# calculate positions of corners for square face
	outer_x = 0.5 * side1
	outer_y = 0.5 * side2

	inner_x = outer_x - wall
	inner_y = outer_y - wall

	# create new part with the PartDesign workbench
	App.newDocument("IBeamTube")
	App.activeDocument().addObject('PartDesign::Body','Body')

	# create sketch on the front plane
	App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch')
	App.activeDocument().Sketch.Support = (App.activeDocument().XZ_Plane, [''])
	App.activeDocument().Sketch.MapMode = 'FlatFace'

	# sketch outer square
	geoList = []
	geoList.append(Part.LineSegment(App.Vector(-outer_x,-outer_y,0),App.Vector(outer_x,-outer_y,0)))  # bottom edge
	geoList.append(Part.LineSegment(App.Vector(outer_x,-outer_y,0),App.Vector(outer_x,outer_y,0)))  # right edge
	geoList.append(Part.LineSegment(App.Vector(outer_x,outer_y,0),App.Vector(-outer_x,outer_y,0)))  # top edge
	geoList.append(Part.LineSegment(App.Vector(-outer_x,outer_y,0),App.Vector(-outer_x,-outer_y,0)))  # left edge
	App.ActiveDocument.Sketch.addGeometry(geoList,False)

##	# constraints needed for fillet anchors
##	conList = []
##	conList.append(Sketcher.Constraint('Coincident',0,2,1,1))
##	conList.append(Sketcher.Constraint('Coincident',1,2,2,1))
##	conList.append(Sketcher.Constraint('Coincident',2,2,3,1))
##	conList.append(Sketcher.Constraint('Coincident',3,2,0,1))
##	conList.append(Sketcher.Constraint('Horizontal',0))
##	conList.append(Sketcher.Constraint('Horizontal',2))
##	conList.append(Sketcher.Constraint('Vertical',1))
##	conList.append(Sketcher.Constraint('Vertical',3))
##	App.ActiveDocument.Sketch.addConstraint(conList)

##	# sketch inner square
##	geoList = []
##	geoList.append(Part.LineSegment(App.Vector(-inner_x,-inner_y,0),App.Vector(inner_x,-inner_y,0)))
##	geoList.append(Part.LineSegment(App.Vector(inner_x,-inner_y,0),App.Vector(inner_x,inner_y,0)))
##	geoList.append(Part.LineSegment(App.Vector(inner_x,inner_y,0),App.Vector(-inner_x,inner_y,0)))
##	geoList.append(Part.LineSegment(App.Vector(-inner_x,inner_y,0),App.Vector(-inner_x,-inner_y,0)))
##	App.ActiveDocument.Sketch.addGeometry(geoList,False)

##	# constraints for fillets
##	conList = []
##	conList.append(Sketcher.Constraint('Coincident',4,2,5,1))
##	conList.append(Sketcher.Constraint('Coincident',5,2,6,1))
##	conList.append(Sketcher.Constraint('Coincident',6,2,7,1))
##	conList.append(Sketcher.Constraint('Coincident',7,2,4,1))
##	conList.append(Sketcher.Constraint('Horizontal',4))
##	conList.append(Sketcher.Constraint('Horizontal',6))
##	conList.append(Sketcher.Constraint('Vertical',5))
##	conList.append(Sketcher.Constraint('Vertical',7))
##	App.ActiveDocument.Sketch.addConstraint(conList)

	# consider end cuts (center-to-center) in length calculation
	if e1angle == 90:
		if e2angle == 90:
			length = length

		else:
			length = length + (side1 * math.tan(math.radians(90 - e2angle)) / 2) # () is midpoint of endcut from top-axis

	elif e2angle == 90:
		length = length + (side1 * math.tan(math.radians(90 - e1angle)) / 2)

	else:
		length = length +  (side1 * math.tan(math.radians(90 - e1angle)) / 2) + (side1 * math.tan(math.radians(90 - e2angle)) / 2)

	# boss extrude the sketch
	App.activeDocument().Body.newObject("PartDesign::Pad","Pad")
	App.activeDocument().Pad.Profile = App.activeDocument().Sketch
	App.ActiveDocument.Pad.Length = length
	App.ActiveDocument.recompute()  # requires recompute after each feature

	# create sketch on the front plane to cut I-Beam shape
	App.activeDocument().Body.newObject('Sketcher::SketchObject','SketchIBeamCut')
	App.activeDocument().SketchIBeamCut.Support = (App.activeDocument().XZ_Plane, [''])
	App.activeDocument().SketchIBeamCut.MapMode = 'FlatFace'

	# sketch squares to be removed
	# Two squares, one going from -outery to -1/2wall, the other going from 1/2wall to outery
	geoList = []
	geoList.append(Part.LineSegment(App.Vector(-inner_x,-outer_y,0),App.Vector(inner_x,-outer_y,0)))  # bottom edge
	geoList.append(Part.LineSegment(App.Vector(inner_x,-outer_y,0),App.Vector(inner_x,(-1/2 * wall),0)))  # right edge
	geoList.append(Part.LineSegment(App.Vector(inner_x,(-1/2 * wall),0),App.Vector(-inner_x,(-1/2 * wall),0)))  # top edge
	geoList.append(Part.LineSegment(App.Vector(-inner_x,(-1/2 * wall),0),App.Vector(-inner_x,-outer_y,0)))  # left edge
	App.ActiveDocument.SketchIBeamCut.addGeometry(geoList,False)

	geoList = []
	geoList.append(Part.LineSegment(App.Vector(-inner_x,(1/2 * wall),0),App.Vector(inner_x,(1/2 * wall),0)))  # bottom edge
	geoList.append(Part.LineSegment(App.Vector(inner_x,(1/2 * wall),0),App.Vector(inner_x,outer_y,0)))  # right edge
	geoList.append(Part.LineSegment(App.Vector(inner_x,outer_y,0),App.Vector(-inner_x,outer_y,0)))  # top edge
	geoList.append(Part.LineSegment(App.Vector(-inner_x,outer_y,0),App.Vector(-inner_x,(1/2 * wall),0)))  # left edge
	App.ActiveDocument.SketchIBeamCut.addGeometry(geoList,False)



	# extrude cut the squares
	App.activeDocument().Body.newObject("PartDesign::Pocket","PocketIBeamCut")
	App.activeDocument().PocketIBeamCut.Profile = App.activeDocument().SketchIBeamCut
	App.ActiveDocument.PocketIBeamCut.Length = 1000000000 # measured in mm, excessively high to account for any sized length
	App.ActiveDocument.PocketIBeamCut.Length2 = 1000000000
	App.ActiveDocument.PocketIBeamCut.Type = 4
	App.ActiveDocument.recompute()

##	# fillet edges
##	App.getDocument('CChannelTube').getObject('Body').newObject('PartDesign::Fillet','Fillet')
##	App.getDocument('CChannelTube').getObject('Fillet').Radius = cradius * 0.8 # passed value of cradius too large
##	App.getDocument('CChannelTube').getObject('Fillet').Base = (App.getDocument('CChannelTube').getObject('PocketCChannelCut'),["Edge21","Edge9","Edge24"])
##	App.getDocument('CChannelTube').recompute()

	# create sketches for end cuts
	App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch001') # front
	App.activeDocument().Sketch001.Support = (App.activeDocument().YZ_Plane, [''])
	App.activeDocument().Sketch001.MapMode = 'FlatFace'

	App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch003') # top
	App.activeDocument().Sketch003.Support = (App.activeDocument().XY_Plane, [''])
	App.activeDocument().Sketch003.MapMode = 'FlatFace'



	# determine location of end cuts
	y = side1 / 2
	x1 = -length
	if e1angle < 0:
		e1angle = 360 - e1angle
	if e2angle < 0:
		e2angle = 360 - e2angle
	x = -side1 / math.tan(math.radians(e2angle))
	x2 = x1 + (side1 / math.tan(math.radians(e1angle)))

	# sketch first end cut
	if e1cutside == 1 and e1angle != 90:
		App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(x1,-y,0),App.Vector(x2,y,0)),False)
		App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(x2,y,0),App.Vector(x1,y,0)),False)
		App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(x1,y,0),App.Vector(x1,-y,0)),False)

		App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket001")
		App.activeDocument().Pocket001.Profile = App.activeDocument().Sketch001
		App.ActiveDocument.Pocket001.Length = 1000
		App.ActiveDocument.Pocket001.Length2 = 1000
		App.ActiveDocument.Pocket001.Type = 4
		App.ActiveDocument.recompute()

	elif e1cutside == 2 and e1angle!= 90:
		y = side1 / 2
		x1 = -length
		x = -side1 / math.tan(math.radians(e2angle))
		x2 = x1 + (side1 / math.tan(math.radians(e1angle)))

		App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(-y,x1,0),App.Vector(y,x2,0)),False)
		App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(y,x2,0),App.Vector(y,x1,0)),False)
		App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(y,x1,0),App.Vector(-y,x1,0)),False)

		App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket003")
		App.activeDocument().Pocket003.Profile = App.activeDocument().Sketch003
		App.ActiveDocument.Pocket003.Length = 1000
		App.ActiveDocument.Pocket003.Length2 = 1000
		App.ActiveDocument.Pocket003.Type = 4
		App.ActiveDocument.recompute()

	# determine rotation of end cuts
	if roffset == 0:

		# sketch second end cut
		if e2angle != 90:

			if e2cutside == 1:
				App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(0,-y,0),App.Vector(x,y,0)),False)
				App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(x,y,0),App.Vector(0,y,0)),False)
				App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(0,y,0),App.Vector(0,-y,0)),False)

				# extrude cut the end cuts
				App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket002")
				App.activeDocument().Pocket002.Profile = App.activeDocument().Sketch001
				App.ActiveDocument.Pocket002.Length = 1000
				App.ActiveDocument.Pocket002.Length2 = 1000
				App.ActiveDocument.Pocket002.Type = 4
				App.ActiveDocument.recompute()

			elif e2cutside == 2:
				App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(-y,0,0),App.Vector(y,x,0)),False)
				App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(y,x,0),App.Vector(y,0,0)),False)
				App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(y,0,0),App.Vector(-y,0,0)),False)

				# extrude cut the end cuts
				App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket004")
				App.activeDocument().Pocket004.Profile = App.activeDocument().Sketch003
				App.ActiveDocument.Pocket004.Length = 1000
				App.ActiveDocument.Pocket004.Length2 = 1000
				App.ActiveDocument.Pocket004.Type = 4
				App.ActiveDocument.recompute()



##	elif roffset == 90:
##
##		# extrude cut the first end cut
##		if e1angle != 90 and e1cutside == 1:
##			App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket")
##			App.activeDocument().Pocket.Profile = App.activeDocument().Sketch001
##			App.ActiveDocument.Pocket.Length = 1000
##			App.ActiveDocument.Pocket.Length2 = 1000
##			App.ActiveDocument.Pocket.Type = 4
##			App.ActiveDocument.recompute()
##
##		# adjust for roffset
##		x = side2 / 2
##		x1 = -length
##		x2 = x1 - x
##		y = -side2 / math.tan(math.radians(e2angle))
##
##		if e2angle != 90:
##			# create sketch for second end cut
##			App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch002')
##			App.activeDocument().Sketch002.Support = (App.activeDocument().XY_Plane, [''])
##			App.activeDocument().Sketch002.MapMode = 'FlatFace'
##
##			# sketch second end cut
##			App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(-x,0,0),App.Vector(-x,y,0)),False)
##			App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(-x,y,0),App.Vector(x,0,0)),False)
##			App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(x,0,0),App.Vector(-x,0,0)),False)
##
##			# extrude cut the second end cut
##			App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket001")
##			App.activeDocument().Pocket001.Profile = App.activeDocument().Sketch002
##			App.ActiveDocument.Pocket001.Length = 1000
##			App.ActiveDocument.Pocket001.Length2 = 1000
##			App.ActiveDocument.Pocket001.Type = 4
##			App.ActiveDocument.recompute()

	elif roffset == 180:  # parallel

		if e2angle != 90:

			# sketch second end cut
			if e2cutside == 1:
				App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(x,-y,0),App.Vector(0,y,0)),False)
				App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(0,y,0),App.Vector(0,-y,0)),False)
				App.ActiveDocument.Sketch001.addGeometry(Part.LineSegment(App.Vector(0,-y,0),App.Vector(x,-y,0)),False)

				# extrude cut the end cuts
				App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket002")
				App.activeDocument().Pocket002.Profile = App.activeDocument().Sketch001
				App.ActiveDocument.Pocket002.Length = 1000
				App.ActiveDocument.Pocket002.Length2 = 1000
				App.ActiveDocument.Pocket002.Type = 4
				App.ActiveDocument.recompute()

			elif e2cutside == 2:
				App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(-y,x,0),App.Vector(y,0,0)),False)
				App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(y,0,0),App.Vector(-y,0,0)),False)
				App.ActiveDocument.Sketch003.addGeometry(Part.LineSegment(App.Vector(-y,0,0),App.Vector(-y,x,0)),False)

				# extrude cut the end cuts
				App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket004")
				App.activeDocument().Pocket004.Profile = App.activeDocument().Sketch003
				App.ActiveDocument.Pocket004.Length = 1000
				App.ActiveDocument.Pocket004.Length2 = 1000
				App.ActiveDocument.Pocket004.Type = 4
				App.ActiveDocument.recompute()


##	elif roffset == 270:
##
##		# extrude cut the first end cut
##		if e1angle != 90 and e1cutside == 1:
##			App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket")
##			App.activeDocument().Pocket.Profile = App.activeDocument().Sketch001
##			App.ActiveDocument.Pocket.Length = side2
##			App.ActiveDocument.Pocket.Length2 = side2
##			App.ActiveDocument.Pocket.Type = 4
##			App.ActiveDocument.recompute()
##
##		# adjust for roffset
##		x = side2 / 2
##		x1 = -length
##		x2 = x1 - x
##		y = -side2 / math.tan(math.radians(e2angle))
##
##		if e2angle != 90:
##
##			# create sketch for second end cut
##			App.activeDocument().Body.newObject('Sketcher::SketchObject','Sketch002')
##			App.activeDocument().Sketch002.Support = (App.activeDocument().XY_Plane, [''])
##			App.activeDocument().Sketch002.MapMode = 'FlatFace'
##
##			# sketch second end cut
##			App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(x,0,0),App.Vector(x,y,0)),False)
##			App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(x,y,0),App.Vector(-x,0,0)),False)
##			App.ActiveDocument.Sketch002.addGeometry(Part.LineSegment(App.Vector(-x,0,0),App.Vector(x,0,0)),False)
##
##			# extrude cut the second end cut
##			App.activeDocument().Body.newObject("PartDesign::Pocket","Pocket001")
##			App.activeDocument().Pocket001.Profile = App.activeDocument().Sketch002
##			App.ActiveDocument.Pocket001.Length = 1000
##			App.ActiveDocument.Pocket001.Length2 = 1000
##			App.ActiveDocument.Pocket001.Type = 4
##			App.ActiveDocument.recompute()

	# rotate tube to fit horizontally in PieceMaker window
	App.getDocument("IBeamTube").Body.Placement=App.Placement(App.Vector(0,0,0), App.Rotation(90,0,0), App.Vector(0,0,0))

	# render and save STL file
	global __objs__
	__objs__=[]
	__objs__.append(FreeCAD.getDocument("IBeamTube").getObject("Body"))





'''FEATURE GENERATION'''
# generate circle features for tube
def circle_feature(xdist, ros, diameter, ydist, arr_inc, arr_inst, length, material_type, o_0, o_90, o_180, o_270):


	#For flat bar, the only orientation that actually exists is the 270 one.  Therefore, o_0 becomes o_270 internally.
	if material_type == 4:
		o_270 = o_0
		o_0 = 0

	#For angle-iron, only the o_180 and o_270 orientations exist.  Therefore, o_0 becomes o_270 and o_90 becomes o_180 internally.
	if material_type == 3:
		o_270 = o_0
		o_180 = o_90
		#o_0 = 0
		#o_90 = 0

	#For C-Channel, the o_90 orientation does not exist.  Therefore, o_90 becomes o_270 internally.
	if material_type == 5:
		o_270 = o_90
		o_90 = 0

	global sketch_counter
	o_counter = 1 # represents which orientation the loop is on

	for orientation in [o_0, o_90, o_180, o_270]:

		sc = str(sketch_counter)

		# only cut that side if it was selected
		if orientation == True:

			# sketch creation, FreeCAD requires dynamically named executable statements because of its method structure
			exec('App.activeDocument().Body.newObject("Sketcher::SketchObject","CircleFeatureSketch" + sc)')

			# right plane
			if o_counter == 1 or o_counter == 3:
				exec('App.activeDocument().CircleFeatureSketch' + sc + '.Support = (App.activeDocument().YZ_Plane, [''])')

			# top plane
			elif o_counter == 2 or o_counter == 4:
				exec('App.activeDocument().CircleFeatureSketch' + sc + '.Support = (App.activeDocument().XY_Plane, [''])')

			exec('App.activeDocument().CircleFeatureSketch' + sc + '.MapMode = "FlatFace"')
			App.ActiveDocument.recompute()

			# calculations
			x_feat_location = -length + xdist
			radius = diameter / 2

			# iterate over array of feature type
			for instance in range(arr_inst):

				# sketch circle
				if o_counter == 1 or o_counter == 3:
					exec('App.ActiveDocument.CircleFeatureSketch' + sc + '.addGeometry(Part.Circle(App.Vector(' + str(x_feat_location + instance * arr_inc) + ',ydist,0),App.Vector(0,0,1),radius),False)')

				elif o_counter == 2 or o_counter == 4:
					exec('App.ActiveDocument.CircleFeatureSketch' + sc + '.addGeometry(Part.Circle(App.Vector(ydist,' + str(x_feat_location + instance * arr_inc) + ',0),App.Vector(0,0,1),radius),False)')

			# extrude cut feature
			exec('App.activeDocument().Body.newObject("PartDesign::Pocket","CircleFeaturePocket" + sc)')
			exec('App.activeDocument().CircleFeaturePocket' + sc + '.Profile = App.activeDocument().CircleFeatureSketch' + sc)
			exec('App.activeDocument().CircleFeaturePocket' + sc + '.Length = 5.0')
			App.ActiveDocument.recompute()

			exec('App.ActiveDocument.CircleFeaturePocket' + sc + '.Length = 1000.00000')
			exec('App.ActiveDocument.CircleFeaturePocket' + sc + '.Length2 = 1000.0000')

			if material_type == 3:  # angle iron
				#exec('App.ActiveDocument.CircleFeaturePocket' + sc + '.Type = 4')  # 'Two Dimensions'
				exec('App.ActiveDocument.CircleFeaturePocket' + sc + '.Type = 1')  # 'Through All'
			else:
				exec('App.ActiveDocument.CircleFeaturePocket' + sc + '.Type = 1')  # 'Through All'

			exec('App.ActiveDocument.CircleFeaturePocket' + sc + '.UpToFace = None')

			# 0 and 90
			if o_counter == 1 or o_counter == 2:
				exec('App.ActiveDocument.CircleFeaturePocket' + sc + '.Reversed = 1')

			# reverse side of cut for 180 and 270
			elif o_counter == 3 or o_counter == 4:
				exec('App.ActiveDocument.CircleFeaturePocket' + sc + '.Reversed = 0')

			exec('App.ActiveDocument.CircleFeaturePocket' + sc + '.Midplane = 0')
			exec('App.ActiveDocument.CircleFeaturePocket' + sc + '.Offset = 0.000000')
			App.ActiveDocument.recompute()

			sketch_counter += 1

		o_counter += 1

# generate rectangular features for tube
def rectangle_feature(xdist, ros, diameter, sep, ydist, arr_inc, arr_inst, length, material_type, o_0, o_90, o_180, o_270):

	global sketch_counter
	o_counter = 1 # represents which orientation the loop is on

	for orientation in [o_0, o_90, o_180, o_270]:

		sc = str(sketch_counter)

		# only cut that side if it was selected
		if orientation == True:

			# sketch creation, FreeCAD requires dynamically named executable statements because of its method structure
			exec('App.activeDocument().Body.newObject("Sketcher::SketchObject","RectangleFeatureSketch" + sc)')

			# right plane
			if o_counter == 1 or o_counter == 3:
				exec('App.activeDocument().RectangleFeatureSketch' + sc + '.Support = (App.activeDocument().YZ_Plane, [''])')

			# top plane
			elif o_counter == 2 or o_counter == 4:
				exec('App.activeDocument().RectangleFeatureSketch' + sc + '.Support = (App.activeDocument().XY_Plane, [''])')

			exec('App.activeDocument().RectangleFeatureSketch' + sc + '.MapMode = "FlatFace"')
			App.ActiveDocument.recompute()

			# calculations
			x_feat_location = -length + xdist

			# calculate positions of corners for rectangle
			rect_x = 0.5 * sep  # positive x coordinate
			rect_y = 0.5 * sep
			rect_nx = -0.5 * sep  # negative x coordinate
			rect_ny = -0.5 * sep

			# iterate over array of feature type
			for instance in range(arr_inst):

				# sketch rectangle (right plane)
				if o_counter == 1 or o_counter == 3:

					# recalculate corner coordinates based on array instance
					rect_x = x_feat_location + (diameter/2) + instance * arr_inc
					rect_nx = x_feat_location - (diameter/2) + instance * arr_inc

					# sketch rectangle
					geoList = []
					geoList.append(Part.LineSegment(App.Vector(rect_nx,rect_ny,0),App.Vector(rect_x,rect_ny,0)))  # bottom edge
					geoList.append(Part.LineSegment(App.Vector(rect_x,rect_ny,0),App.Vector(rect_x,rect_y,0)))  # right edge
					geoList.append(Part.LineSegment(App.Vector(rect_x,rect_y,0),App.Vector(rect_nx,rect_y,0)))  # top edge
					geoList.append(Part.LineSegment(App.Vector(rect_nx,rect_y,0),App.Vector(rect_nx,rect_ny,0)))  # left edge
					exec('App.ActiveDocument.RectangleFeatureSketch' + sc + '.addGeometry(geoList,False)')

					conList = []
					conList.append(Sketcher.Constraint('Coincident',0 + (4 * instance),2,1 + (4 * instance),1))
					conList.append(Sketcher.Constraint('Coincident',1 + (4 * instance),2,2 + (4 * instance),1))
					conList.append(Sketcher.Constraint('Coincident',2 + (4 * instance),2,3 + (4 * instance),1))
					conList.append(Sketcher.Constraint('Coincident',3 + (4 * instance),2,0 + (4 * instance),1))
					conList.append(Sketcher.Constraint('Horizontal',0 + (4 * instance)))
					conList.append(Sketcher.Constraint('Horizontal',2 + (4 * instance)))
					conList.append(Sketcher.Constraint('Vertical',1 + (4 * instance)))
					conList.append(Sketcher.Constraint('Vertical',3 + (4 * instance)))
					exec('App.ActiveDocument.RectangleFeatureSketch' + sc + '.addConstraint(conList)')
					App.ActiveDocument.recompute()

				# sketch rectangle (top plane)
				elif o_counter == 2 or o_counter == 4:

					# move coordinates based on feature location
					rect_y = x_feat_location + (diameter/2) + instance * arr_inc
					rect_ny = x_feat_location - (diameter/2) + instance * arr_inc

					# sketch rectangle
					geoList = []
					geoList.append(Part.LineSegment(App.Vector(rect_nx,rect_ny,0),App.Vector(rect_x,rect_ny,0)))  # bottom edge
					geoList.append(Part.LineSegment(App.Vector(rect_x,rect_ny,0),App.Vector(rect_x,rect_y,0)))  # right edge
					geoList.append(Part.LineSegment(App.Vector(rect_x,rect_y,0),App.Vector(rect_nx,rect_y,0)))  # top edge
					geoList.append(Part.LineSegment(App.Vector(rect_nx,rect_y,0),App.Vector(rect_nx,rect_ny,0)))  # left edge
					exec('App.ActiveDocument.RectangleFeatureSketch' + sc + '.addGeometry(geoList,False)')

					conList = []
					conList.append(Sketcher.Constraint('Coincident',0 + (4 * instance),2,1 + (4 * instance),1))
					conList.append(Sketcher.Constraint('Coincident',1 + (4 * instance),2,2 + (4 * instance),1))
					conList.append(Sketcher.Constraint('Coincident',2 + (4 * instance),2,3 + (4 * instance),1))
					conList.append(Sketcher.Constraint('Coincident',3 + (4 * instance),2,0 + (4 * instance),1))
					conList.append(Sketcher.Constraint('Horizontal',0 + (4 * instance)))
					conList.append(Sketcher.Constraint('Horizontal',2 + (4 * instance)))
					conList.append(Sketcher.Constraint('Vertical',1 + (4 * instance)))
					conList.append(Sketcher.Constraint('Vertical',3 + (4 * instance)))
					exec('App.ActiveDocument.RectangleFeatureSketch' + sc + '.addConstraint(conList)')
					App.ActiveDocument.recompute()

			# extrude cut feature
			exec('App.activeDocument().Body.newObject("PartDesign::Pocket","RectangleFeaturePocket" + sc)')
			exec('App.activeDocument().RectangleFeaturePocket' + sc + '.Profile = App.activeDocument().RectangleFeatureSketch' + sc)
			exec('App.activeDocument().RectangleFeaturePocket' + sc + '.Length = 5.0')
			App.ActiveDocument.recompute()

			exec('App.ActiveDocument.RectangleFeaturePocket' + sc + '.Length = 1000.00000')
			exec('App.ActiveDocument.RectangleFeaturePocket' + sc + '.Length2 = 1000.0000')

			if material_type == 3:  # angle iron
				exec('App.ActiveDocument.RectangleFeaturePocket' + sc + '.Type = 4')  # 'Two Dimensions'
			else:
				exec('App.ActiveDocument.RectangleFeaturePocket' + sc + '.Type = 1')  # 'Through All'

			exec('App.ActiveDocument.RectangleFeaturePocket' + sc + '.UpToFace = None')

			# 0 and 90
			if o_counter == 1 or o_counter == 2:
				exec('App.ActiveDocument.RectangleFeaturePocket' + sc + '.Reversed = 1')

			# reverse side of cut for 180 and 270
			elif o_counter == 3 or o_counter == 4:
				exec('App.ActiveDocument.RectangleFeaturePocket' + sc + '.Reversed = 0')

			exec('App.ActiveDocument.RectangleFeaturePocket' + sc + '.Midplane = 0')
			exec('App.ActiveDocument.RectangleFeaturePocket' + sc + '.Offset = 0.000000')
			App.ActiveDocument.recompute()

			sketch_counter += 1

		o_counter += 1

# generate slot features for tube
def slot_feature(xdist, ros, diameter, sep, ydist, arr_inc, arr_inst, length, material_type, o_0,o_90, o_180, o_270):

	global sketch_counter
	o_counter = 1 # represents which orientation the loop is on

	for orientation in [o_0, o_90, o_180, o_270]:

		sc = str(sketch_counter)

		# only cut that side if it was selected
		if orientation == True:

			# sketch creation, FreeCAD requires dynamically named executable statements because of its method structure
			exec('App.activeDocument().Body.newObject("Sketcher::SketchObject","SlotFeatureSketch" + sc)')

			# right plane
			if o_counter == 1 or o_counter == 3:
				exec('App.activeDocument().SlotFeatureSketch' + sc + '.Support = (App.activeDocument().YZ_Plane, [''])')

			# top plane
			elif o_counter == 2 or o_counter == 4:
				exec('App.activeDocument().SlotFeatureSketch' + sc + '.Support = (App.activeDocument().XY_Plane, [''])')

			exec('App.activeDocument().SlotFeatureSketch' + sc + '.MapMode = "FlatFace"')
			App.ActiveDocument.recompute()

			# calculations
			x_feat_location = -length + xdist
			radius = diameter / 2

			# calculate positions of corners for square face
			slot_x = 0.5 * diameter # outer positive x coordinate
			slot_y = 0.5 * diameter
			slot_nx = -0.5 * diameter # outer negative x coordinate
			slot_ny = -0.5 * diameter

			# iterate over array of feature type
			for instance in range(arr_inst):

				# sketch feature
				if o_counter == 1 or o_counter == 3:

					# move coordinates based on feature location
					slot_x = x_feat_location + (sep/2) + (arr_inc * instance)
					slot_nx = x_feat_location - (sep/2) + (arr_inc * instance)

					# sketch slot
					geoList = []
					geoList.append(Part.ArcOfCircle(Part.Circle(App.Vector(slot_nx,0,0),App.Vector(0,0,1),radius),math.pi/2,-math.pi/2)) # left semicircle
					geoList.append(Part.ArcOfCircle(Part.Circle(App.Vector(slot_x,0,0),App.Vector(0,0,1),radius),-math.pi/2,math.pi/2)) # right semicircle
					geoList.append(Part.LineSegment(App.Vector(slot_nx,-radius,0),App.Vector(slot_x,-radius,0))) # bottom line segment
					geoList.append(Part.LineSegment(App.Vector(slot_nx,radius,0),App.Vector(slot_x,radius,0))) # top line segment
					exec('App.ActiveDocument.SlotFeatureSketch' + sc + '.addGeometry(geoList,False)')

					conList = []
					conList.append(Sketcher.Constraint('Tangent',0 + (4 * instance),1,3 + (4 * instance),1))
					conList.append(Sketcher.Constraint('Tangent',0 + (4 * instance),2,2 + (4 * instance),1))
					conList.append(Sketcher.Constraint('Tangent',2 + (4 * instance),2,1 + (4 * instance),1))
					conList.append(Sketcher.Constraint('Tangent',3 + (4 * instance),2,1 + (4 * instance),2))
					conList.append(Sketcher.Constraint('Horizontal',2 + (4 * instance)))
					conList.append(Sketcher.Constraint('Equal',0 + (4 * instance),1 + (4 * instance)))
					exec('App.ActiveDocument.SlotFeatureSketch' + sc + '.addConstraint(conList)')

				elif o_counter == 2 or o_counter == 4:

					# move coordinates based on feature location
					slot_y = x_feat_location + (sep/2) + (arr_inc * instance)
					slot_ny = x_feat_location - (sep/2) + (arr_inc * instance)

					geoList = []
					geoList.append(Part.ArcOfCircle(Part.Circle(App.Vector(0,slot_ny,0),App.Vector(0,0,1),radius),math.pi,0))
					geoList.append(Part.ArcOfCircle(Part.Circle(App.Vector(0,slot_y,0),App.Vector(0,0,1),radius),0,math.pi))
					geoList.append(Part.LineSegment(App.Vector(radius,slot_ny,0),App.Vector(radius,slot_y,0)))
					geoList.append(Part.LineSegment(App.Vector(-radius,slot_ny,0),App.Vector(-radius,slot_y,0)))
					exec('App.ActiveDocument.SlotFeatureSketch' + sc + '.addGeometry(geoList,False)')

					conList = []
					conList.append(Sketcher.Constraint('Tangent',0 + (4 * instance),1,3 + (4 * instance),1))
					conList.append(Sketcher.Constraint('Tangent',0 + (4 * instance),2,2 + (4 * instance),1))
					conList.append(Sketcher.Constraint('Tangent',2 + (4 * instance),2,1 + (4 * instance),1))
					conList.append(Sketcher.Constraint('Tangent',3 + (4 * instance),2,1 + (4 * instance),2))
					conList.append(Sketcher.Constraint('Vertical',2 + (4 * instance)))
					conList.append(Sketcher.Constraint('Equal',0 + (4 * instance),1 + (4 * instance)))
					exec('App.ActiveDocument.SlotFeatureSketch' + sc + '.addConstraint(conList)')

			# extrude cut feature
			exec('App.activeDocument().Body.newObject("PartDesign::Pocket","SlotFeaturePocket" + sc)')
			exec('App.activeDocument().SlotFeaturePocket' + sc + '.Profile = App.activeDocument().SlotFeatureSketch' + sc)
			exec('App.activeDocument().SlotFeaturePocket' + sc + '.Length = 5.0')
			App.ActiveDocument.recompute()

			exec('App.ActiveDocument.SlotFeaturePocket' + sc + '.Length = 1000.00000')
			exec('App.ActiveDocument.SlotFeaturePocket' + sc + '.Length2 = 1000.0000')

			if material_type == 3:  # angle iron
				exec('App.ActiveDocument.SlotFeaturePocket' + sc + '.Type = 4')  # 'Two Dimensions'
			else:
				exec('App.ActiveDocument.SlotFeaturePocket' + sc + '.Type = 1')  # 'Through All'

			exec('App.ActiveDocument.SlotFeaturePocket' + sc + '.UpToFace = None')

			# 0 and 90
			if o_counter == 1 or o_counter == 2:
				exec('App.ActiveDocument.SlotFeaturePocket' + sc + '.Reversed = 1')

			# reverse side of cut for 180 and 270
			if o_counter == 3 or o_counter == 4:
				exec('App.ActiveDocument.SlotFeaturePocket' + sc + '.Reversed = 0')

			exec('App.ActiveDocument.SlotFeaturePocket' + sc + '.Midplane = 0')
			exec('App.ActiveDocument.SlotFeaturePocket' + sc + '.Offset = 0.000000')
			App.ActiveDocument.recompute()

			sketch_counter += 1

		o_counter += 1


# run total tube generation
set_paths()